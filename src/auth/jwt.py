import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import status

from src.errors import AppError


@dataclass
class TokenPayload:
    user_id: uuid.UUID
    token_type: str
    jti: uuid.UUID | None = None


def create_access_token(user_id: uuid.UUID, *, secret: str, algorithm: str, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def create_refresh_token(
    user_id: uuid.UUID, jti: uuid.UUID, *, secret: str, algorithm: str, expires_days: int
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(jti),
        "iat": now,
        "exp": now + timedelta(days=expires_days),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str, expected_type: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError as exc:
        raise AppError("TOKEN_INVALID", "Sessão inválida ou expirada.", status.HTTP_401_UNAUTHORIZED) from exc

    if payload.get("type") != expected_type:
        raise AppError("TOKEN_INVALID", "Sessão inválida ou expirada.", status.HTTP_401_UNAUTHORIZED)

    jti = uuid.UUID(payload["jti"]) if payload.get("jti") else None
    return TokenPayload(user_id=uuid.UUID(payload["sub"]), token_type=payload["type"], jti=jti)
