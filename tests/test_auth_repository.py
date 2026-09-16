import uuid

from src.auth.repository import GoogleIdentityRepository
from src.users.repository import UserRepository


async def test_create_and_get_by_google_sub(db_session):
    user = await UserRepository(db_session).create(email="carla@example.com", name="Carla")
    repository = GoogleIdentityRepository(db_session)

    identity = await repository.create(user_id=user.id, google_sub="sub-1", email="carla@example.com")

    found = await repository.get_by_google_sub("sub-1")
    assert found is not None
    assert found.id == identity.id
    assert found.user_id == user.id


async def test_get_by_user_id(db_session):
    user = await UserRepository(db_session).create(email="bruno@example.com", name="Bruno")
    repository = GoogleIdentityRepository(db_session)
    await repository.create(user_id=user.id, google_sub="sub-2", email="bruno@example.com")

    found = await repository.get_by_user_id(user.id)

    assert found is not None
    assert found.google_sub == "sub-2"


async def test_get_by_google_sub_returns_none_when_not_found(db_session):
    repository = GoogleIdentityRepository(db_session)

    found = await repository.get_by_google_sub("does-not-exist")

    assert found is None


async def test_set_refresh_jti_updates_value(db_session):
    user = await UserRepository(db_session).create(email="duda@example.com", name="Duda")
    repository = GoogleIdentityRepository(db_session)
    identity = await repository.create(user_id=user.id, google_sub="sub-3", email="duda@example.com")

    jti = uuid.uuid4()
    await repository.set_refresh_jti(identity, jti)

    assert identity.current_refresh_jti == jti
