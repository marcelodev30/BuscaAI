from dataclasses import dataclass

from fastapi import status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from starlette.concurrency import run_in_threadpool

from src.errors import AppError


@dataclass
class GoogleClaims:
    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str | None


async def verify_google_id_token(token: str, client_id: str) -> GoogleClaims:
    try:
        claims = await run_in_threadpool(
            google_id_token.verify_oauth2_token, token, google_requests.Request(), client_id
        )
    except ValueError as exc:
        raise AppError(
            "GOOGLE_TOKEN_INVALID", "Token do Google inválido ou expirado.", status.HTTP_401_UNAUTHORIZED
        ) from exc

    email = claims.get("email")
    if not email:
        raise AppError("GOOGLE_TOKEN_INVALID", "Token do Google inválido ou expirado.", status.HTTP_401_UNAUTHORIZED)

    return GoogleClaims(
        sub=claims["sub"],
        email=email,
        email_verified=bool(claims.get("email_verified", False)),
        name=claims.get("name") or email,
        picture=claims.get("picture"),
    )
