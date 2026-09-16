import uuid

from fastapi import status

from src.api.routes import auth as auth_route
from src.auth.google import GoogleClaims
from src.db.models import UserStatus
from src.errors import AppError
from src.users.repository import UserRepository


def _fake_claims(**overrides):
    defaults = dict(
        sub="google-sub-abc",
        email="giulia@example.com",
        email_verified=True,
        name="Giulia",
        picture=None,
    )
    defaults.update(overrides)
    return GoogleClaims(**defaults)


async def _fake_verify(id_token, client_id):
    return _fake_claims()


def test_login_with_google_creates_user(client, monkeypatch):
    monkeypatch.setattr(auth_route, "verify_google_id_token", _fake_verify)

    response = client.post("/v1/auth/google", json={"id_token": "whatever"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "giulia@example.com"
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_with_google_reuses_existing_identity(client, monkeypatch):
    monkeypatch.setattr(auth_route, "verify_google_id_token", _fake_verify)

    first = client.post("/v1/auth/google", json={"id_token": "whatever"})
    second = client.post("/v1/auth/google", json={"id_token": "whatever"})

    assert first.json()["user"]["id"] == second.json()["user"]["id"]


def test_login_with_google_links_existing_user_by_verified_email(client, monkeypatch):
    async def _verify_first(id_token, client_id):
        return _fake_claims(sub="sub-1")

    monkeypatch.setattr(auth_route, "verify_google_id_token", _verify_first)
    first = client.post("/v1/auth/google", json={"id_token": "t1"})

    async def _verify_second(id_token, client_id):
        return _fake_claims(sub="sub-2")

    monkeypatch.setattr(auth_route, "verify_google_id_token", _verify_second)
    second = client.post("/v1/auth/google", json={"id_token": "t2"})

    assert first.json()["user"]["id"] == second.json()["user"]["id"]


def test_login_with_google_rejects_invalid_token(client, monkeypatch):
    async def _raise(id_token, client_id):
        raise AppError("GOOGLE_TOKEN_INVALID", "Token do Google inválido ou expirado.", status.HTTP_401_UNAUTHORIZED)

    monkeypatch.setattr(auth_route, "verify_google_id_token", _raise)

    response = client.post("/v1/auth/google", json={"id_token": "bad"})

    assert response.status_code == 401
    assert response.json()["code"] == "GOOGLE_TOKEN_INVALID"


async def test_login_with_google_rejects_disabled_user(client, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(auth_route, "verify_google_id_token", _fake_verify)
    login = client.post("/v1/auth/google", json={"id_token": "whatever"})
    user_id = uuid.UUID(login.json()["user"]["id"])

    async with db_sessionmaker() as session:
        user = await UserRepository(session).get_by_id(user_id)
        user.status = UserStatus.disabled
        await session.commit()

    response = client.post("/v1/auth/google", json={"id_token": "whatever"})

    assert response.status_code == 403
    assert response.json()["code"] == "USER_DISABLED"


def test_refresh_rotates_token_and_rejects_reuse(client, monkeypatch):
    monkeypatch.setattr(auth_route, "verify_google_id_token", _fake_verify)
    login = client.post("/v1/auth/google", json={"id_token": "whatever"})
    old_refresh = login.json()["refresh_token"]

    first_refresh = client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first_refresh.status_code == 200
    assert first_refresh.json()["refresh_token"] != old_refresh

    reused = client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert reused.json()["code"] == "TOKEN_INVALID"


def test_refresh_rejects_access_token(client, monkeypatch):
    monkeypatch.setattr(auth_route, "verify_google_id_token", _fake_verify)
    login = client.post("/v1/auth/google", json={"id_token": "whatever"})
    access_token = login.json()["access_token"]

    response = client.post("/v1/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_INVALID"
