import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import File
from src.domain.file_state import FileStatus


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

    async def get_for_processing(self, file_id: uuid.UUID) -> File | None:
        """Sem filtro de user_id: o processamento é interno, disparado pelo
        próprio backend, e nunca a partir de um id vindo do cliente."""
        return await self.session.get(File, file_id)

    async def mark_processing(self, file: File) -> None:
        file.status = FileStatus.processing
        file.progress = 0
        file.error_code = None
        file.error_message = None
        await self.session.flush()

    async def mark_stage(self, file: File, stage: str, progress: int) -> None:
        file.stage = stage
        file.progress = progress
        await self.session.flush()

    async def mark_ready(self, file: File, *, chunk_count: int, storage_key: str) -> None:
        file.status = FileStatus.ready
        file.stage = None
        file.progress = 100
        file.chunk_count = chunk_count
        file.storage_key = storage_key
        file.indexed_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_empty(self, file: File, *, storage_key: str) -> None:
        file.status = FileStatus.empty
        file.stage = None
        file.progress = 100
        file.chunk_count = 0
        file.storage_key = storage_key
        await self.session.flush()

    async def mark_failed(self, file: File, *, error_code: str, error_message: str) -> None:
        file.status = FileStatus.failed
        file.stage = None
        file.error_code = error_code
        file.error_message = error_message
        await self.session.flush()

    async def sum_pages_since(self, user_id: uuid.UUID, since: datetime) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(File.page_count), 0)).where(
                File.user_id == user_id, File.created_at >= since, File.deleted_at.is_(None)
            )
        )
        return result.scalar_one()
