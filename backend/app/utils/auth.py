import hashlib
import logging
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import Session, User

logger = logging.getLogger(__name__)
settings = get_settings()

SESSION_MAX_AGE = 2592000  # 30 days


def set_session_cookie(response: Response, token: str) -> None:
    """Set the session_token HttpOnly cookie on a FastAPI response.

    Development (local):
      - SameSite="lax"
      - Secure=False (HTTP allowed on localhost)
      - Domain="localhost"

    Production (cross-site Vercel → Railway):
      - SameSite="none" (REQUIRED for cross-site fetch/axios withCredentials)
      - Secure=True    (MANDATORY when SameSite="none")
      - HttpOnly=True  (prevents XSS token theft)
      - Domain=None    (host-only cookie scoped to backend domain)
      - Path="/"
    """
    env_is_dev = settings.environment.lower() == "development"
    samesite = "lax" if env_is_dev else "none"
    secure = not env_is_dev
    cookie_domain = "localhost" if env_is_dev else None

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite=samesite,
        max_age=SESSION_MAX_AGE,
        secure=secure,
        domain=cookie_domain,
        path="/",
    )
    logger.info(
        "[auth-cookie] Cookie set: key=session_token, httponly=True, secure=%s, samesite=%s, domain=%s, path=/, max_age=%s",
        secure,
        samesite,
        cookie_domain,
        SESSION_MAX_AGE,
    )


def delete_session_cookie(response: Response) -> None:
    """Delete the session_token cookie from the client browser."""
    env_is_dev = settings.environment.lower() == "development"
    samesite = "lax" if env_is_dev else "none"
    secure = not env_is_dev
    cookie_domain = "localhost" if env_is_dev else None

    response.delete_cookie(
        key="session_token",
        httponly=True,
        samesite=samesite,
        secure=secure,
        domain=cookie_domain,
        path="/",
    )
    logger.info(
        "[auth-cookie] Cookie deleted: key=session_token, httponly=True, secure=%s, samesite=%s, domain=%s, path=/",
        secure,
        samesite,
        cookie_domain,
    )


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
    cookie_present = bool(token)
    logger.info(
        "[auth] /me cookie present=%s (cookies_received=%s)",
        cookie_present,
        list(request.cookies.keys()),
    )
    if not token:
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
