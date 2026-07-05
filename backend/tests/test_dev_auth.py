from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.routers import auth as auth_router


@pytest.mark.asyncio
async def test_create_dev_session_creates_user_and_session():
    auth_router.settings.environment = "development"

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: None),
            SimpleNamespace(scalar_one_or_none=lambda: None),
        ]
    )
    db.flush = AsyncMock()

    token = await auth_router.create_dev_session(db)

    assert token
    assert db.add.call_count >= 2
    assert db.flush.await_count >= 1
