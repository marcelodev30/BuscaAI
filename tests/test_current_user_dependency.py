import uuid

import pytest

from src.auth.dependencies import get_current_user
from src.auth.jwt import create_access_token
from src.config import get_settings
from src.db.models import UserStatus
from src.errors import AppError
from src.users.repository import UserRepository


async def test_get_current_user_returns_user_for_valid_token(db_session):
    user = await UserRepository(db_session).create(email="elis@example.com", name="Elis")
    settings = get_settings()
    token = create_access_token(
        user.id, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm, expires_minutes=5
    )

    result = await get_current_user(authorization=f"Bearer {token}", db=db_session)

    assert result.id == user.id


async def test_get_current_user_rejects_missing_header(db_session):
    with pytest.raises(AppError):
        await get_current_user(authorization=None, db=db_session)


async def test_get_current_user_rejects_malformed_header(db_session):
    with pytest.raises(AppError):
        await get_current_user(authorization="not-a-bearer-token", db=db_session)


async def test_get_current_user_rejects_disabled_user(db_session):
    user = await UserRepository(db_session).create(email="fabio@example.com", name="Fabio")
    user.status = UserStatus.disabled
    await db_session.flush()

    settings = get_settings()
    token = create_access_token(
        user.id, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm, expires_minutes=5
    )

    with pytest.raises(AppError):
        await get_current_user(authorization=f"Bearer {token}", db=db_session)


async def test_get_current_user_rejects_unknown_user(db_session):
    settings = get_settings()
    token = create_access_token(
        uuid.uuid4(), secret=settings.jwt_secret, algorithm=settings.jwt_algorithm, expires_minutes=5
    )

    with pytest.raises(AppError):
        await get_current_user(authorization=f"Bearer {token}", db=db_session)
