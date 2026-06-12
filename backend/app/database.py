import logging
import ssl
from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_async_connect_args(database_url: str, environment: str) -> dict:
    """Supabase pooler requires SSL; asyncpg on Windows fails strict cert verify in dev."""
    if "supabase" not in database_url and "pooler.supabase.com" not in database_url:
        return {}
    if environment == "development":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}
    return {"ssl": True}


_connect_args = _build_async_connect_args(settings.database_url, settings.environment)

engine = create_async_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    import app.models  # noqa: F401 — register models with Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def test_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        return False


# ── Startup schema validation ────────────────────────────────────


def _sqla_col_to_ddl(col) -> str:
    """Convert a SQLAlchemy Column type to a Postgres DDL snippet."""
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
    from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, BigInteger

    col_type = type(col.type)
    if col_type is Text or (col_type is String and (col.type.length or 0) > 500):
        ddl = "TEXT"
    elif col_type is String:
        ddl = f"VARCHAR({col.type.length})"
    elif col_type is Integer:
        ddl = "INTEGER"
    elif col_type is BigInteger:
        ddl = "BIGINT"
    elif col_type is Float:
        ddl = "FLOAT"
    elif col_type is Boolean:
        ddl = "BOOLEAN"
    elif col_type is DateTime:
        ddl = "TIMESTAMP WITH TIME ZONE" if col.type.timezone else "TIMESTAMP"
    elif col_type is UUID:
        ddl = "UUID"
    elif col_type is JSONB:
        ddl = "JSONB"
    elif col_type is ARRAY:
        ddl = "VARCHAR[]"
    else:
        ddl = "TEXT"  # safe fallback

    # Add DEFAULT clause if server_default is set
    if col.server_default is not None:
        default_text = col.server_default.arg
        if hasattr(default_text, "text"):
            default_text = default_text.text
        ddl += f" DEFAULT {default_text}"

    return ddl


async def validate_schema() -> dict[str, list[str]]:
    """Compare SQLAlchemy model metadata against live PostgreSQL schema.

    Returns a dict of {table_name: [missing_column_names]} for any mismatches found.
    Auto-fixes missing columns by adding them to the database.
    """
    import app.models  # noqa: F401 — ensure models are registered

    all_missing: dict[str, list[str]] = {}

    async with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            table_name = table.name

            # Get actual DB columns
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t"
            ), {"t": table_name})
            db_cols = {row[0] for row in result.fetchall()}

            if not db_cols:
                # Table doesn't exist yet — init_db / create_all will handle it
                continue

            model_cols = {col.name for col in table.columns}
            missing = model_cols - db_cols

            if missing:
                all_missing[table_name] = sorted(missing)
                logger.warning(
                    "SCHEMA MISMATCH: table '%s' is missing %d column(s): %s",
                    table_name, len(missing), ", ".join(sorted(missing)),
                )

    # Auto-fix missing columns
    if all_missing:
        logger.info("Auto-fixing %d table(s) with missing columns...", len(all_missing))
        async with engine.begin() as conn:
            for table_name, missing_cols in all_missing.items():
                sa_table = Base.metadata.tables[table_name]
                for col_name in missing_cols:
                    sa_col = sa_table.columns[col_name]
                    ddl = _sqla_col_to_ddl(sa_col)
                    sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {ddl}"
                    try:
                        await conn.execute(text(sql))
                        logger.info("  ADDED column %s.%s (%s)", table_name, col_name, ddl)
                    except Exception as e:
                        logger.error("  FAILED to add %s.%s: %s", table_name, col_name, e)

        # Re-verify
        async with engine.connect() as conn:
            still_missing = {}
            for table_name in all_missing:
                result = await conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :t"
                ), {"t": table_name})
                db_cols = {row[0] for row in result.fetchall()}
                model_cols = {col.name for col in Base.metadata.tables[table_name].columns}
                remaining = model_cols - db_cols
                if remaining:
                    still_missing[table_name] = sorted(remaining)

            if still_missing:
                logger.error("SCHEMA FIX INCOMPLETE — still missing: %s", still_missing)
            else:
                logger.info("Schema validation: all tables in sync")
    else:
        logger.info("Schema validation: all tables in sync")

    return all_missing
