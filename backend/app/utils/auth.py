import hashlib
import logging
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Session, User

logger = logging.getLogger(__name__)


def create_session_token() -> str:
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def verify_session(token: str, db: AsyncSession) -> User | None:
    token_hash = hash_token(token)
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.user))
        .where(Session.token == token_hash)
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        return None

    return session.user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get("session_token")
    if not token:
        logger.warning(
            "[auth] /me missing session_token cookie. cookies_received=%s",
            list(request.cookies.keys()),
        )
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await verify_session(token, db)
    if user is None:
        logger.warning("[auth] session lookup failed for token_hash=%s…", hash_token(token)[:12])
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = request.cookies.get("session_token")
    if not token:
        return None
    return await verify_session(token, db)
