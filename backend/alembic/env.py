import asyncio
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

import app.models  # noqa: F401
from app.config import get_settings
from app.database import Base

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Convert async URLs to sync format for migrations
sync_url = settings.database_url
# Convert PostgreSQL async to sync
sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")
# Convert SQLite async to sync
sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
config.set_main_option(
    "sqlalchemy.url",
    sync_url.replace("%", "%%"),
)


def _sync_connect_args() -> dict:
    if "supabase" in sync_url:
        return {"sslmode": "require"}
    return {}


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = sync_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with sync psycopg2 (reliable for Supabase pooler)."""
    connectable = create_engine(
        sync_url,
        poolclass=pool.NullPool,
        connect_args=_sync_connect_args(),
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


async def run_async_migrations() -> None:
    """Legacy async path — kept for reference; not used."""
    from sqlalchemy.ext.asyncio import async_engine_from_config

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
