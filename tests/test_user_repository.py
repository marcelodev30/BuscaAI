import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from src.db.models import UserStatus
from src.users.repository import UserRepository


async def test_create_sets_defaults(db_session):
    repository = UserRepository(db_session)

    user = await repository.create(email="ana@example.com", name="Ana")

    assert user.id is not None
    assert user.status == UserStatus.active
    assert user.plan == "free"
    assert user.email_verified is False


async def test_get_by_id_returns_created_user(db_session):
    repository = UserRepository(db_session)
    created = await repository.create(email="bruno@example.com", name="Bruno")

    found = await repository.get_by_id(created.id)

    assert found is not None
    assert found.email == "bruno@example.com"


async def test_get_by_id_returns_none_when_not_found(db_session):
    repository = UserRepository(db_session)

    found = await repository.get_by_id(uuid.uuid4())

    assert found is None


async def test_get_by_email_returns_created_user(db_session):
    repository = UserRepository(db_session)
    await repository.create(email="carla@example.com", name="Carla")

    found = await repository.get_by_email("carla@example.com")

    assert found is not None
    assert found.name == "Carla"


async def test_get_by_email_returns_none_when_not_found(db_session):
    repository = UserRepository(db_session)

    found = await repository.get_by_email("inexistente@example.com")

    assert found is None


async def test_email_must_be_unique(db_session):
    repository = UserRepository(db_session)
    await repository.create(email="duplicado@example.com", name="Primeiro")

    with pytest.raises(IntegrityError):
        await repository.create(email="duplicado@example.com", name="Segundo")
