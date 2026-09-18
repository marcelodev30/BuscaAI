import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import File


class FileRepository:
    """Assim como em notebooks, o ownership vive na query: nada é devolvido sem
    o filtro de user_id (PRD §17, CLAUDE.md §13)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        original_name: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str,
        page_count: int,
        source_key: str,
    ) -> File:
        file = File(
            id=file_id,
            user_id=user_id,
            notebook_id=notebook_id,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            page_count=page_count,
            source_key=source_key,
        )
        self.session.add(file)
        await self.session.flush()
        return file

    async def list_by_notebook(self, notebook_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[File]:
        result = await self.session.execute(
            select(File)
            .where(File.notebook_id == notebook_id, File.user_id == user_id, File.deleted_at.is_(None))
            .order_by(File.created_at.desc())
        )
        return result.scalars().all()

    async def count_by_notebook(self, notebook_id: uuid.UUID, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(File)
            .where(File.notebook_id == notebook_id, File.user_id == user_id, File.deleted_at.is_(None))
        )
        return result.scalar_one()

    async def sum_pages_since(self, user_id: uuid.UUID, since: datetime) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(File.page_count), 0)).where(
                File.user_id == user_id, File.created_at >= since, File.deleted_at.is_(None)
            )
        )
        return result.scalar_one()
