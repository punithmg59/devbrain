import httpx
import logging
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.utils.redis_client import get_redis, is_redis_available
from app.security.encryption import get_encryption_service, EncryptionError

logger = logging.getLogger(__name__)
TOKEN_TTL = 2592000  # 30 days


async def save_github_token(user: User, access_token: str, db: AsyncSession) -> None:
    """Encrypt and save GitHub access token.
    
    The token is encrypted before storing in the database and Redis.
    """
    try:
        encryption_service = get_encryption_service()
        
        # Encrypt token with user context binding
        user_context = str(user.id).encode('utf-8')
        encrypted_token = await encryption_service.encrypt(
            access_token,
            associated_data=user_context,
        )
        
        user.github_access_token = encrypted_token
        
        # Also cache encrypted token in Redis
        if is_redis_available():
            await get_redis().setex(f"ghtoken:{user.id}", TOKEN_TTL, encrypted_token)
            
    except EncryptionError as e:
        logger.error("Failed to encrypt GitHub token for user %s: %s", user.id, e)
        raise HTTPException(
            status_code=500,
            detail="Failed to securely store GitHub token"
        ) from e


async def clear_github_token(user: User) -> None:
    user.github_access_token = None
    if is_redis_available():
        await get_redis().delete(f"ghtoken:{user.id}")


async def get_github_token(user: User, db: AsyncSession) -> str:
    """Decrypt and return GitHub access token.
    
    The token is decrypted from the database or Redis cache.
    """
    encryption_service = get_encryption_service()
    user_context = str(user.id).encode('utf-8')
    
    # Try Redis cache first
    if is_redis_available():
        encrypted_token = await get_redis().get(f"ghtoken:{user.id}")
        if encrypted_token:
            try:
                decrypted_token = await encryption_service.decrypt(
                    encrypted_token,
                    associated_data=user_context,
                )
                return decrypted_token
            except EncryptionError as e:
                logger.warning("Failed to decrypt cached token for user %s: %s", user.id, e)
                # Fall through to database
    
    # Try database
    if user.github_access_token:
        try:
            decrypted_token = await encryption_service.decrypt(
                user.github_access_token,
                associated_data=user_context,
            )
            
            # Cache decrypted token in Redis for future use
            if is_redis_available():
                await get_redis().setex(
                    f"ghtoken:{user.id}",
                    TOKEN_TTL,
                    user.github_access_token  # Store encrypted version
                )
            
            return decrypted_token
        except EncryptionError as e:
            logger.error("Failed to decrypt GitHub token for user %s: %s", user.id, e)
            raise HTTPException(
                status_code=500,
                detail="Failed to decrypt GitHub token"
            ) from e

    raise HTTPException(
        status_code=401,
        detail="GitHub token expired. Please log in again.",
    )


async def fetch_github_repos(access_token: str) -> list[dict]:
    repos: list[dict] = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                "https://api.github.com/user/repos",
                params={"per_page": 100, "page": page, "sort": "updated"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=30.0,
            )
            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="GitHub token invalid. Please log in again.",
                )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    return repos
