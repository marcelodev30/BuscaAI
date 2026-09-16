import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.google import verify_google_id_token
from src.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.auth.repository import GoogleIdentityRepository
from src.auth.schemas import AuthResponse, GoogleAuthRequest, RefreshRequest
from src.config import Settings, get_settings
from src.db.models import GoogleIdentity, User, UserStatus
from src.db.session import get_db
from src.errors import AppError
from src.users.repository import UserRepository
from src.users.schemas import UserOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _issue_tokens(user_id: uuid.UUID, jti: uuid.UUID, settings: Settings) -> tuple[str, str]:
    access_token = create_access_token(
        user_id,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_access_expires_minutes,
    )
    refresh_token_value = create_refresh_token(
        user_id,
        jti,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_days=settings.jwt_refresh_expires_days,
    )
    return access_token, refresh_token_value


def _ensure_active(user: User) -> None:
    if user.status != UserStatus.active:
        raise AppError("USER_DISABLED", "Esta conta está desativada.", status.HTTP_403_FORBIDDEN)


@router.post("/google", response_model=AuthResponse)
async def login_with_google(payload: GoogleAuthRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    settings = get_settings()
    claims = await verify_google_id_token(payload.id_token, settings.google_client_id)

    users = UserRepository(db)
    identities = GoogleIdentityRepository(db)

    identity = await identities.get_by_google_sub(claims.sub)
    if identity is not None:
        user = await users.get_by_id(identity.user_id)
    else:
        user = await users.get_by_email(claims.email) if claims.email_verified else None
        if user is None:
            user = await users.create(
                email=claims.email,
                name=claims.name,
                avatar_url=claims.picture,
                email_verified=claims.email_verified,
            )

        existing_identity = await identities.get_by_user_id(user.id)
        if existing_identity is not None:
            # O sub do Google mudou para este usuário (ver PRD §6, passo 4: fallback
            # por e-mail verificado). Atualiza em vez de criar uma segunda identidade,
            # já que a relação user <-> google_identity é 1:1.
            await identities.update_google_sub(existing_identity, google_sub=claims.sub, email=claims.email)
            identity = existing_identity
        else:
            identity = await identities.create(user_id=user.id, google_sub=claims.sub, email=claims.email)

    _ensure_active(user)

    user.last_login_at = datetime.now(timezone.utc)

    jti = uuid.uuid4()
    await identities.set_refresh_jti(identity, jti)
    access_token, refresh_token_value = _issue_tokens(user.id, jti, settings)

    return AuthResponse(access_token=access_token, refresh_token=refresh_token_value, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=AuthResponse)
async def refresh_session(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    settings = get_settings()
    token_payload = decode_token(
        payload.refresh_token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm, expected_type="refresh"
    )

    users = UserRepository(db)
    identities = GoogleIdentityRepository(db)

    user = await users.get_by_id(token_payload.user_id)
    identity: GoogleIdentity | None = await identities.get_by_user_id(token_payload.user_id) if user else None

    if user is None or identity is None or identity.current_refresh_jti != token_payload.jti:
        raise AppError("TOKEN_INVALID", "Sessão inválida ou expirada.", status.HTTP_401_UNAUTHORIZED)

    _ensure_active(user)

    new_jti = uuid.uuid4()
    await identities.set_refresh_jti(identity, new_jti)
    access_token, refresh_token_value = _issue_tokens(user.id, new_jti, settings)

    return AuthResponse(access_token=access_token, refresh_token=refresh_token_value, user=UserOut.model_validate(user))
