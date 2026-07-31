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
    """Supabase pooler requires SSL; asyncpg on Windows fails strict cert verify in dev.
    
    IMPORTANT: PgBouncer transaction pooling (pooler.supabase.com:6543) does not support
    prepared statements. Must set statement_cache_size=0 to avoid DuplicatePreparedStatementError.
    """
    # Check if using Supabase (either pooler or direct connection)
    is_supabase = "supabase" in database_url or "pooler.supabase.com" in database_url
    
    if not is_supabase:
        return {}
    
    # Build SSL context
    if environment == "development":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ssl_arg = ctx
    else:
        ctx = ssl.create_default_context()
        ssl_arg = ctx
    
    # CRITICAL: statement_cache_size=0 is required for PgBouncer transaction pooling
    return {"ssl": ssl_arg, "statement_cache_size": 0}


# Fix: Use session pooling port (5432) instead of transaction pooling (6543)
# Transaction pooling doesn't support prepared statements, causing DuplicatePreparedStatementError
# Session pooling supports prepared statements and is compatible with SQLAlchemy/asyncpg
database_url = settings.database_url.replace(':6543', ':5432')

_connect_args = _build_async_connect_args(database_url, settings.environment)

engine = create_async_engine(
    database_url,
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


# SQL keywords and function calls that must NOT be quoted when used as DEFAULT values.
_PG_BARE_KEYWORDS: frozenset[str] = frozenset({
    "NULL", "TRUE", "FALSE",
    "NOW()", "CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME",
    "GEN_RANDOM_UUID()",
})


def _sqla_col_to_ddl(col) -> str:
    """Convert a SQLAlchemy Column object to a PostgreSQL DDL type + default snippet.

    Handles:
    - All common SQLAlchemy scalar types (Integer, Float, Boolean, BigInteger,
      String, Text, DateTime, UUID, JSONB, ARRAY).
    - server_default values of all kinds: numeric literals, boolean keywords,
      SQL functions (now(), gen_random_uuid()), cast expressions ('{}'::jsonb),
      and plain string literals that require quoting ('low', 'pending', etc.).
    - ARRAY element type is preserved (e.g. ARRAY(String) → TEXT[]).
    - String columns without an explicit length are mapped to TEXT.
    - nullable=False columns get NOT NULL appended.
    """
    from sqlalchemy import (
        BigInteger,
        Boolean,
        DateTime,
        Float,
        Integer,
        String,
        Text,
    )
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

    col_type = type(col.type)

    # ------------------------------------------------------------------
    # Step 1: Resolve the PostgreSQL type string.
    # ------------------------------------------------------------------
    if col_type is Text:
        pg_type = "TEXT"
    elif col_type is String:
        # String() with no length → use TEXT to avoid VARCHAR(None) crash.
        length = col.type.length
        pg_type = "TEXT" if length is None or length > 500 else f"VARCHAR({length})"
    elif col_type is Integer:
        pg_type = "INTEGER"
    elif col_type is BigInteger:
        pg_type = "BIGINT"
    elif col_type is Float:
        pg_type = "DOUBLE PRECISION"
    elif col_type is Boolean:
        pg_type = "BOOLEAN"
    elif col_type is DateTime:
        pg_type = "TIMESTAMP WITH TIME ZONE" if col.type.timezone else "TIMESTAMP"
    elif col_type is UUID:
        pg_type = "UUID"
    elif col_type is JSONB:
        pg_type = "JSONB"
    elif col_type is ARRAY:
        # Preserve the element type so ARRAY(Integer) → INTEGER[] not VARCHAR[].
        item_type = col.type.item_type
        item_pg = {
            Text: "TEXT",
            String: "TEXT",
            Integer: "INTEGER",
            BigInteger: "BIGINT",
            Float: "DOUBLE PRECISION",
            Boolean: "BOOLEAN",
        }.get(type(item_type), "TEXT")
        pg_type = f"{item_pg}[]"
    else:
        pg_type = "TEXT"

    ddl = pg_type

    # ------------------------------------------------------------------
    # Step 2: Resolve the DEFAULT clause.
    #
    # server_default.arg can be:
    #   a) A TextClause  (from text("gen_random_uuid()") or text("now()"))
    #      → extract .text to get the raw SQL string
    #   b) A FunctionElement (from func.now())
    #      → str() produces "now()" — valid raw SQL
    #   c) A plain str  (from server_default="low" or server_default="0")
    #      → needs quoting logic applied
    # ------------------------------------------------------------------
    if col.server_default is not None:
        raw = col.server_default.arg

        # TextClause: extract the embedded SQL string.
        if hasattr(raw, "text"):
            raw_str = raw.text.strip()
        else:
            raw_str = str(raw).strip()

        default_clause = _resolve_default_clause(raw_str, col_type, col.type, col_type is JSONB, col_type is ARRAY)
        ddl += f" DEFAULT {default_clause}"

    # ------------------------------------------------------------------
    # Step 3: Append nullability.
    # ------------------------------------------------------------------
    if not col.nullable:
        ddl += " NOT NULL"

    return ddl


def _resolve_default_clause(
    raw: str,
    col_type: type,
    sqla_type,
    is_jsonb: bool,
    is_array: bool,
) -> str:
    """Given a raw default string from SQLAlchemy, return a safe PostgreSQL DEFAULT expression.

    Rules applied in order:
    1. Already fully-formed PostgreSQL expressions (contain '::') → pass through unchanged.
    2. Already single-quoted literals → pass through unchanged.
    3. Known SQL keywords / functions (TRUE, FALSE, NOW(), etc.) → pass through unchanged.
    4. Looks numeric (int or float literal) → pass through unchanged.
    5. JSONB column with bare JSON literal → quote and cast: 'value'::jsonb
    6. ARRAY column with bare array literal → quote and cast: 'value'::text[]
    7. String / Text column → quote as string literal: 'value'
    8. Anything else → pass through unchanged (let PostgreSQL validate it).
    """
    from sqlalchemy import String, Text
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB

    # Rule 1: already a cast expression.
    if "::" in raw:
        return raw

    # Rule 2: already quoted.
    if raw.startswith("'") and raw.endswith("'"):
        return raw

    # Rule 3: SQL keyword / function — never quote these.
    if raw.upper() in _PG_BARE_KEYWORDS:
        return raw

    # Rule 4: numeric literal — never quote.
    try:
        float(raw)  # catches "0", "0.0", "-1", "3.14"
        return raw
    except ValueError:
        pass

    # Rule 5: JSONB column.
    if is_jsonb:
        # e.g. "[]" → '[]'::jsonb,  "{}" → '{}'::jsonb
        return f"'{raw}'::jsonb"

    # Rule 6: ARRAY column.
    if is_array:
        # e.g. "{}" → '{}'::text[]
        item_pg = "text"  # safe fallback; array element type already in the column DDL
        return f"'{raw}'::{item_pg}[]"

    # Rule 7: string-like column types need quoting.
    if isinstance(sqla_type, (String, Text)):
        # Escape any embedded single quotes.
        escaped = raw.replace("'", "''")
        return f"'{escaped}'"

    # Rule 8: everything else — pass through and let PostgreSQL decide.
    return raw


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

    # Auto-fix missing columns.
    # CRITICAL: each ALTER TABLE runs in its own independent transaction.
    # PostgreSQL poisons an entire transaction on any DDL error, so a single
    # shared engine.begin() block would roll back all previously-successful
    # columns the moment one fails. One transaction per column avoids this.
    if all_missing:
        logger.info("Auto-fixing %d table(s) with missing columns...", len(all_missing))
        for table_name, missing_cols in all_missing.items():
            sa_table = Base.metadata.tables[table_name]
            for col_name in missing_cols:
                sa_col = sa_table.columns[col_name]
                try:
                    ddl = _sqla_col_to_ddl(sa_col)
                except Exception as e:
                    logger.error(
                        "  FAILED to build DDL for %s.%s — skipping: %s",
                        table_name, col_name, e,
                    )
                    continue

                sql = (
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN IF NOT EXISTS {col_name} {ddl}"
                )
                # Each column gets its own transaction so that a failure on
                # column N does not roll back successfully-added columns 1..N-1.
                try:
                    async with engine.begin() as conn:
                        await conn.execute(text(sql))
                    logger.info(
                        "  ✓ ADDED column %s.%s  DDL: %s",
                        table_name, col_name, ddl,
                    )
                except Exception as e:
                    logger.error(
                        "  ✗ FAILED to add %s.%s  DDL: %s  Error: %s",
                        table_name, col_name, ddl, e,
                    )

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
