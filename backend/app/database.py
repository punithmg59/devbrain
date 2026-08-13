import asyncio
import logging
import os
import ssl
import tempfile
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON, TypeDecorator, Uuid

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Known system CA bundle path on Debian/Ubuntu (installed by ca-certificates package).
# This is the path that `python:3.12-slim` + `apt-get install ca-certificates` provides.
_DEBIAN_CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"


# ── Dialect-aware portable types ─────────────────────────────────────────────
# These are used by all model files instead of the PostgreSQL-specific dialect
# types directly. On PostgreSQL they use the native types (JSONB, ARRAY, UUID);
# on SQLite they fall back to portable equivalents.

def _is_postgresql(url: str) -> bool:
    return url.startswith("postgresql")


class _DialectJSON(TypeDecorator):
    """Stores JSON. Uses JSONB on PostgreSQL, JSON on SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class _DialectArray(_DialectJSON):
    """Stores list-of-strings. Uses ARRAY(String) on PostgreSQL, JSON on SQLite."""
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy import String
            from sqlalchemy.dialects.postgresql import ARRAY
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value  # ARRAY handles natively
        return value  # JSON handles natively (list → JSON text)

    def process_result_value(self, value, dialect):
        if isinstance(value, str):
            import json
            return json.loads(value)
        return value if value is not None else []


class _DialectUUID(TypeDecorator):
    """UUID column. Uses postgresql.UUID on PostgreSQL, sqlalchemy.Uuid on SQLite."""
    impl = Uuid
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(Uuid())


# Public aliases used by model files
DialectJSON = _DialectJSON
DialectArray = _DialectArray
DialectUUID = _DialectUUID


def _build_ssl_context(
    environment: str,
    ca_cert_path: str | None = None,
    ca_cert_inline: str | None = None,
) -> ssl.SSLContext | None:
    """Build and return an ssl.SSLContext for asyncpg, or None for non-SSL drivers.

    CA Certificate resolution order (production only):
      1. DATABASE_SSL_CA_CERT_PATH  — path to a PEM file on disk (highest priority)
      2. DATABASE_SSL_CA_CERT       — inline PEM content written to a temp file
      3. Debian system CA bundle    — /etc/ssl/certs/ca-certificates.crt (Docker)
      4. Python default CA bundle   — auto-discovered by ssl module (fallback)

    Development:
      Hostname verification is relaxed (CERT_NONE) for Windows environments
      where asyncpg cannot verify Supabase's cert chain through the OS cert store.
      CERT_NONE is NEVER used in production.

    Returns:
        ssl.SSLContext — always returned (either verified or relaxed for dev)
    """
    is_dev = environment.lower() == "development"

    if is_dev:
        # Local dev: relax cert verification so developers on Windows can connect.
        # This is intentional and must NEVER appear in production.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        logger.warning(
            "[DB-SSL] Certificate verification DISABLED — development mode only. "
            "This message must NEVER appear in production Railway logs."
        )
        return ctx

    # ── Production: full certificate verification ─────────────────────────────
    # Determine which CA file to use, in priority order.
    _tmp_file = None  # keep reference to prevent GC of NamedTemporaryFile
    ca_file: str | None = None
    ca_source: str = "unknown"

    try:
        if ca_cert_path:
            # Priority 1: explicit file path from DATABASE_SSL_CA_CERT_PATH
            if not os.path.isfile(ca_cert_path):
                raise FileNotFoundError(
                    f"DATABASE_SSL_CA_CERT_PATH points to a non-existent file: {ca_cert_path!r}. "
                    "Download the Supabase CA cert from Dashboard → Database → SSL."
                )
            ca_file = ca_cert_path
            ca_source = f"DATABASE_SSL_CA_CERT_PATH ({ca_cert_path})"
            logger.info("[DB-SSL] Using Supabase CA certificate from path: %s", ca_cert_path)

        elif ca_cert_inline:
            # Priority 2: inline PEM from DATABASE_SSL_CA_CERT env var.
            # Railway stores secrets as env vars; this avoids filesystem concerns.
            # Normalise escaped newlines that shells/Railway may encode as literal \n.
            pem_content = ca_cert_inline.replace("\\n", "\n")
            if not pem_content.strip().startswith("-----BEGIN"):
                raise ValueError(
                    "DATABASE_SSL_CA_CERT does not look like a valid PEM certificate. "
                    "Ensure it starts with '-----BEGIN CERTIFICATE-----'."
                )
            # Write to a temporary file so ssl.create_default_context(cafile=) can load it.
            # We keep _tmp_file alive for the lifetime of this function; the returned ctx
            # holds the loaded cert in memory, so the file can be deleted after load.
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pem", delete=False, prefix="supabase_ca_"
            ) as tmp:
                tmp.write(pem_content)
                _tmp_file = tmp.name
            ca_file = _tmp_file
            ca_source = "DATABASE_SSL_CA_CERT (inline env var)"
            logger.info("[DB-SSL] Using Supabase CA certificate from inline DATABASE_SSL_CA_CERT")

        elif os.path.isfile(_DEBIAN_CA_BUNDLE):
            # Priority 3: Debian system CA bundle (docker image with ca-certificates installed).
            ca_file = _DEBIAN_CA_BUNDLE
            ca_source = f"system CA bundle ({_DEBIAN_CA_BUNDLE})"
            logger.info("[DB-SSL] Using system CA bundle: %s", _DEBIAN_CA_BUNDLE)

        else:
            # Priority 4: Python auto-discovers the platform CA bundle.
            # Works on macOS / CI. On Linux without ca-certificates this may fail.
            ca_file = None
            ca_source = "Python default CA bundle (auto-discovered)"
            logger.warning(
                "[DB-SSL] No explicit CA certificate configured and system CA bundle not found at %s. "
                "Falling back to Python default CA bundle. "
                "Set DATABASE_SSL_CA_CERT_PATH or install ca-certificates to ensure "
                "Supabase certificate verification succeeds.",
                _DEBIAN_CA_BUNDLE,
            )

        ctx = ssl.create_default_context(cafile=ca_file)
        # Explicitly assert both checks are active — defaults, but stated for auditability.
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        logger.info(
            "[DB-SSL] SSL context ready: CERT_REQUIRED + check_hostname=True. CA source: %s",
            ca_source,
        )
        return ctx

    finally:
        # Clean up the temporary file if we wrote one (cert is now loaded in ctx).
        if _tmp_file and os.path.exists(_tmp_file):
            try:
                os.unlink(_tmp_file)
            except OSError:
                pass  # Non-fatal; temp files are cleaned up at process exit anyway.


def _build_async_connect_args(
    database_url: str,
    environment: str,
    ca_cert_path: str | None = None,
    ca_cert_inline: str | None = None,
) -> dict:
    """Build asyncpg connect_args dict for a Supabase/PostgreSQL connection.

    For non-Supabase URLs (e.g. local PostgreSQL, SQLite) returns {}.

    Args:
        database_url:   The full database URL (credentials not logged).
        environment:    'development' relaxes cert verification; anything else is production.
        ca_cert_path:   Path to Supabase CA PEM file (DATABASE_SSL_CA_CERT_PATH).
        ca_cert_inline: Inline PEM content           (DATABASE_SSL_CA_CERT).

    IMPORTANT: PgBouncer/Supavisor transaction pooling (port 6543) does not support
    prepared statements. statement_cache_size=0 avoids DuplicatePreparedStatementError.
    """
    is_supabase = "supabase" in database_url or "pooler.supabase.com" in database_url
    if not is_supabase:
        return {}

    ssl_ctx = _build_ssl_context(environment, ca_cert_path, ca_cert_inline)
    # CRITICAL: statement_cache_size=0 is required for PgBouncer/Supavisor transaction pooling.
    return {"ssl": ssl_ctx, "statement_cache_size": 0}


def log_db_connection_info(database_url: str, connect_args: dict, environment: str) -> None:
    """Log safe connection diagnostics — never logs credentials or certificate contents.

    Logged fields:
        - database host
        - database port
        - SSL enabled
        - CA certificate configured
        - environment
    """
    try:
        parsed = urlparse(database_url)
        host = parsed.hostname or "(unknown)"
        port = parsed.port or "(default)"
    except Exception:
        host = "(parse error)"
        port = "(parse error)"

    ssl_arg = connect_args.get("ssl")
    ssl_enabled = ssl_arg is not None
    ca_configured: str
    if isinstance(ssl_arg, ssl.SSLContext):
        ca_configured = (
            "YES (CERT_REQUIRED)" if ssl_arg.verify_mode == ssl.CERT_REQUIRED
            else "relaxed (CERT_NONE — dev mode)"
        )
    elif ssl_enabled:
        ca_configured = "YES (raw bool)"
    else:
        ca_configured = "N/A"

    logger.info(
        "[DB] Connection info — host: %s | port: %s | SSL enabled: %s | "
        "CA certificate: %s | environment: %s",
        host, port, ssl_enabled, ca_configured, environment,
    )


# Fix: Use session pooling port (5432) instead of transaction pooling (6543)
# Transaction pooling doesn't support prepared statements, causing DuplicatePreparedStatementError
# Session pooling supports prepared statements and is compatible with SQLAlchemy/asyncpg
database_url = settings.database_url.replace(':6543', ':5432')

_connect_args = _build_async_connect_args(
    database_url,
    settings.environment,
    ca_cert_path=settings.database_ssl_ca_cert_path,
    ca_cert_inline=settings.database_ssl_ca_cert,
)

# Log safe diagnostics at module import time (production startup).
log_db_connection_info(database_url, _connect_args, settings.environment)

# SQLite (aiosqlite) uses StaticPool / NullPool and does not support pool_size.
_is_sqlite = database_url.startswith("sqlite")

if _is_sqlite:
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
else:
    engine = create_async_engine(
        database_url,
        connect_args=_connect_args,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=30,   # Raise immediately after 30 s rather than hanging forever.
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
    """Single-attempt connectivity test: executes SELECT 1 and reports result.

    Reports:
        Database connection: OK / FAILED
        Database SSL: OK (if connection succeeded with SSL args in connect_args)
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        ssl_active = bool(_connect_args.get("ssl"))
        logger.info("Database connection: OK")
        logger.info("Database SSL: %s", "OK (verified)" if ssl_active else "N/A (non-SSL driver)")
        logger.info("SELECT 1: OK")
        return True
    except Exception as e:
        err_msg = str(e)
        if "tenant/user" in err_msg or "ENOTFOUND" in err_msg:
            logger.error(
                "\n============================================================\n"
                "SUPABASE DATABASE IS PAUSED OR UNREACHABLE!\n"
                "The error 'tenant/user not found' indicates your free-tier Supabase\n"
                "project has been paused due to inactivity.\n\n"
                "To fix this:\n"
                "1. Go to https://supabase.com/dashboard\n"
                "2. Select your project and click 'Restore Project'\n"
                "3. Wait ~1-2 minutes for project startup and retry.\n"
                "============================================================\n"
            )
        elif "CERTIFICATE_VERIFY_FAILED" in err_msg or "SSL" in err_msg.upper():
            logger.error(
                "\n============================================================\n"
                "DATABASE SSL CERTIFICATE VERIFICATION FAILED!\n"
                "This usually means the Docker image is missing the ca-certificates\n"
                "package, or the Supabase host has changed its certificate chain.\n\n"
                "To diagnose:\n"
                "1. Verify Dockerfile includes: apt-get install ca-certificates\n"
                "2. Verify DATABASE_URL host matches your Supabase project pooler URL\n"
                "3. Check Railway environment variables for PGSSLROOTCERT overrides\n"
                "============================================================\n"
            )
        else:
            # Log the error type and message but never log the DATABASE_URL.
            logger.error("Database connection failed [%s]: %s", type(e).__name__, e)
        return False


async def db_connect_with_backoff(
    max_attempts: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
) -> bool:
    """Attempt database connectivity with exponential backoff.

    Intended for use at application startup to prevent the worker loop from
    entering a tight retry loop when the database is temporarily unreachable.

    Args:
        max_attempts: Maximum number of connection attempts (default 5).
        base_delay:   Initial backoff delay in seconds (default 2 s).
        max_delay:    Maximum backoff delay cap in seconds (default 60 s).

    Returns:
        True if a connection succeeded within max_attempts, False otherwise.
    """
    for attempt in range(1, max_attempts + 1):
        ok = await test_connection()
        if ok:
            return True
        if attempt < max_attempts:
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                "Database connectivity check failed (attempt %d/%d). "
                "Retrying in %.0f s...",
                attempt, max_attempts, delay,
            )
            await asyncio.sleep(delay)
        else:
            logger.error(
                "Database connectivity check FAILED after %d attempts. "
                "Worker loop will NOT start to avoid tight error loop.",
                max_attempts,
            )
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
    """Compare SQLAlchemy model metadata against the live database schema.

    Returns a dict of {table_name: [missing_column_names]} for any mismatches found.
    Auto-fixes missing columns on PostgreSQL by adding them to the database.
    On SQLite, schema auto-fix is skipped (create_all handles this at startup).
    """
    import app.models  # noqa: F401 — ensure models are registered

    dialect = engine.dialect.name
    all_missing: dict[str, list[str]] = {}

    async with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            table_name = table.name

            # Get actual DB columns — method depends on dialect
            if dialect == "sqlite":
                # SQLite: use PRAGMA table_info
                result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
                rows = result.fetchall()
                # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
                db_cols = {row[1] for row in rows}
            else:
                # PostgreSQL: use information_schema
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

    if not all_missing:
        logger.info("Schema validation: all tables in sync")
        return all_missing

    # Auto-fix missing columns — PostgreSQL only.
    # On SQLite, create_all() at startup already handles schema creation and
    # ALTER TABLE ADD COLUMN IF NOT EXISTS is not supported in all SQLite versions.
    if dialect == "sqlite":
        logger.info(
            "Schema validation: SQLite — skipping auto-fix (restart will call create_all). "
            "Missing: %s", all_missing
        )
        return all_missing

    # ── PostgreSQL auto-fix ───────────────────────────────────────────────────
    # CRITICAL: each ALTER TABLE runs in its own independent transaction.
    # PostgreSQL poisons an entire transaction on any DDL error, so a single
    # shared engine.begin() block would roll back all previously-successful
    # columns the moment one fails. One transaction per column avoids this.
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

    return all_missing
