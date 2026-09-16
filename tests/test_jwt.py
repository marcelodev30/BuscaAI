import uuid

import pytest

from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.errors import AppError

SECRET = "test-secret"
ALGORITHM = "HS256"


def test_access_token_round_trip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, secret=SECRET, algorithm=ALGORITHM, expires_minutes=5)

    payload = decode_token(token, secret=SECRET, algorithm=ALGORITHM, expected_type="access")

    assert payload.user_id == user_id
    assert payload.token_type == "access"
    assert payload.jti is None


def test_refresh_token_round_trip():
    user_id = uuid.uuid4()
    jti = uuid.uuid4()
    token = create_refresh_token(user_id, jti, secret=SECRET, algorithm=ALGORITHM, expires_days=7)

    payload = decode_token(token, secret=SECRET, algorithm=ALGORITHM, expected_type="refresh")

    assert payload.user_id == user_id
    assert payload.jti == jti


def test_decode_rejects_wrong_type():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, secret=SECRET, algorithm=ALGORITHM, expires_minutes=5)

    with pytest.raises(AppError):
        decode_token(token, secret=SECRET, algorithm=ALGORITHM, expected_type="refresh")


def test_decode_rejects_expired_token():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, secret=SECRET, algorithm=ALGORITHM, expires_minutes=-1)

    with pytest.raises(AppError):
        decode_token(token, secret=SECRET, algorithm=ALGORITHM, expected_type="access")


def test_decode_rejects_tampered_secret():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, secret=SECRET, algorithm=ALGORITHM, expires_minutes=5)

    with pytest.raises(AppError):
        decode_token(token, secret="wrong-secret", algorithm=ALGORITHM, expected_type="access")
