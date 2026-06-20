"""Test script to verify the PgBouncer fix works with a fresh module import."""
import asyncio
import ssl
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Use the same DATABASE_URL from the environment
from app.config import get_settings
settings = get_settings()

# Build connect args with statement_cache_size=0 for PgBouncer
def build_connect_args(database_url: str, environment: str) -> dict:
    """Supabase pooler requires SSL; asyncpg on Windows fails strict cert verify in dev.
    
    IMPORTANT: PgBouncer transaction pooling (pooler.supabase.com:6543) does not support
    prepared statements. Must set statement_cache_size=0 to avoid DuplicatePreparedStatementError.
    """
    is_supabase = "supabase" in database_url or "pooler.supabase.com" in database_url
    
    if not is_supabase:
        return {}
    
    if environment == "development":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ssl_arg = ctx
    else:
        ssl_arg = True
    
    return {"ssl": ssl_arg, "statement_cache_size": 0}

connect_args = build_connect_args(settings.database_url, settings.environment)
print(f"DATABASE_URL: {settings.database_url}")
print(f"Connect args: {connect_args}")

async def test():
    # Use session pooling port (5432) instead of transaction pooling port (6543)
    # Session pooling supports prepared statements, transaction pooling does not
    database_url = settings.database_url.replace(':6543', ':5432')
    print(f"Using database URL: {database_url}")
    
    engine = create_async_engine(
        database_url,
        connect_args=connect_args,
        echo=False,
    )
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful - NO DuplicatePreparedStatementError")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    result = asyncio.run(test())
    print(f"Test result: {result}")
