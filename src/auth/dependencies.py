from fastapi import Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import decode_token
from src.config import get_settings
from src.db.models import User, UserStatus
from src.db.session import get_db
from src.errors import AppError
from src.users.repository import UserRepository


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

    token = authorization.removeprefix("Bearer ").strip()
    settings = get_settings()
    payload = decode_token(
        token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm, expected_type="access"
    )

    user = await UserRepository(db).get_by_id(payload.user_id)
    if user is None or user.status != UserStatus.active:
        raise AppError("UNAUTHORIZED", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

    return user
