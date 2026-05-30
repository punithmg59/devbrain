import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.utils.redis_client import get_redis, is_redis_available

TOKEN_TTL = 2592000  # 30 days


async def save_github_token(user: User, access_token: str, db: AsyncSession) -> None:
    user.github_access_token = access_token
    if is_redis_available():
        await get_redis().setex(f"ghtoken:{user.id}", TOKEN_TTL, access_token)


async def clear_github_token(user: User) -> None:
    user.github_access_token = None
    if is_redis_available():
        await get_redis().delete(f"ghtoken:{user.id}")


async def get_github_token(user: User, db: AsyncSession) -> str:
    if is_redis_available():
        token = await get_redis().get(f"ghtoken:{user.id}")
        if token:
            return token

    if user.github_access_token:
        if is_redis_available():
            await get_redis().setex(f"ghtoken:{user.id}", TOKEN_TTL, user.github_access_token)
        return user.github_access_token

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
