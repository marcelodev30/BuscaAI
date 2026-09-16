import pytest

from src.auth import google as google_module
from src.errors import AppError


async def test_verify_google_id_token_returns_claims(monkeypatch):
    fake_claims = {
        "sub": "google-sub-123",
        "email": "ana@example.com",
        "email_verified": True,
        "name": "Ana",
        "picture": "https://example.com/pic.png",
    }
    monkeypatch.setattr(google_module.google_id_token, "verify_oauth2_token", lambda *a, **k: fake_claims)

    claims = await google_module.verify_google_id_token("fake-token", "client-id")

    assert claims.sub == "google-sub-123"
    assert claims.email == "ana@example.com"
    assert claims.email_verified is True
    assert claims.name == "Ana"


async def test_verify_google_id_token_rejects_invalid_token(monkeypatch):
    def _raise(*args, **kwargs):
        raise ValueError("Token expired")

    monkeypatch.setattr(google_module.google_id_token, "verify_oauth2_token", _raise)

    with pytest.raises(AppError):
        await google_module.verify_google_id_token("bad-token", "client-id")


async def test_verify_google_id_token_requires_email(monkeypatch):
    monkeypatch.setattr(
        google_module.google_id_token,
        "verify_oauth2_token",
        lambda *a, **k: {"sub": "google-sub-123"},
    )

    with pytest.raises(AppError):
        await google_module.verify_google_id_token("token-without-email", "client-id")
