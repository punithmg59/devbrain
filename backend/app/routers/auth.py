import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Session, User
from app.schemas.auth import UserResponse
from app.utils.auth import create_session_token, get_current_user, hash_token
from app.utils.github import clear_github_token, save_github_token
from app.utils.redis_client import get_redis, is_redis_available

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
settings = get_settings()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

SESSION_MAX_AGE = 2592000  # 30 days


@router.get("/api/auth/github")
async def github_login() -> RedirectResponse:
    if not is_redis_available():
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Auth storage unavailable. Start Redis or run in development mode.",
        )

    state = secrets.token_hex(16)
    redis = get_redis()
    await redis.setex(f"oauth_state:{state}", 600, "1")

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.app_url}/api/auth/github/callback",
        "scope": "read:user user:email repo",
        "state": state,
    }
    authorize_url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=authorize_url, status_code=302)


@router.get("/api/auth/github/callback")
async def github_callback(
    code: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if not code or not state:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?msg=invalid_state",
            status_code=302,
        )

    redis = get_redis()
    state_key = f"oauth_state:{state}"
    stored_state = await redis.get(state_key)
    if not stored_state:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?msg=invalid_state",
            status_code=302,
        )
    await redis.delete(state_key)

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            logger.error("GitHub token exchange failed: %s", token_data)
            return RedirectResponse(
                url=f"{settings.frontend_url}/auth/error?msg=token_exchange_failed",
                status_code=302,
            )

        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = await client.get(GITHUB_USER_URL, headers=headers)
        user_response.raise_for_status()
        github_user = user_response.json()

        emails_response = await client.get(GITHUB_EMAILS_URL, headers=headers)
        emails_response.raise_for_status()
        emails = emails_response.json()

    primary_email: str | None = None
    for entry in emails:
        if entry.get("primary") and entry.get("verified"):
            primary_email = entry.get("email")
            break
    if primary_email is None:
        for entry in emails:
            if entry.get("primary"):
                primary_email = entry.get("email")
                break

    github_id = str(github_user["id"])
    username = github_user.get("login") or github_user.get("name") or github_id
    avatar_url = github_user.get("avatar_url")

    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if user:
        user.username = username
        user.avatar_url = avatar_url
        user.email = primary_email
    else:
        user = User(
            github_id=github_id,
            username=username,
            avatar_url=avatar_url,
            email=primary_email,
            plan="FREE",
        )
        db.add(user)

    await db.flush()

    await save_github_token(user, access_token, db)

    raw_token = create_session_token()
    session = Session(
        user_id=user.id,
        token=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE),
    )
    db.add(session)
    await db.flush()

    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard", status_code=302)
    response.set_cookie(
        key="session_token",
        value=raw_token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        secure=settings.environment != "development",
    )
    return response


@router.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/api/auth/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    token = request.cookies.get("session_token")
    if token:
        token_hash = hash_token(token)
        result = await db.execute(select(Session).where(Session.token == token_hash))
        session = result.scalar_one_or_none()
        if session:
            await db.delete(session)

    await clear_github_token(current_user)

    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="session_token")
    return response
