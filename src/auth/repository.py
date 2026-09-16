import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import GoogleIdentity


class GoogleIdentityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_google_sub(self, google_sub: str) -> GoogleIdentity | None:
        result = await self.session.execute(select(GoogleIdentity).where(GoogleIdentity.google_sub == google_sub))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> GoogleIdentity | None:
        result = await self.session.execute(select(GoogleIdentity).where(GoogleIdentity.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, *, user_id: uuid.UUID, google_sub: str, email: str) -> GoogleIdentity:
        identity = GoogleIdentity(user_id=user_id, google_sub=google_sub, email=email)
        self.session.add(identity)
        await self.session.flush()
        return identity

    async def set_refresh_jti(self, identity: GoogleIdentity, jti: uuid.UUID | None) -> None:
        identity.current_refresh_jti = jti
        await self.session.flush()

    async def update_google_sub(self, identity: GoogleIdentity, *, google_sub: str, email: str) -> None:
        identity.google_sub = google_sub
        identity.email = email
        await self.session.flush()
