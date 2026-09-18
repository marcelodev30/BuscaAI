import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Notebook


class NotebookRepository:
    """As consultas sempre filtram por user_id: o ownership não depende da rota
    lembrar de aplicá-lo (PRD §17, CLAUDE.md §13)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, user_id: uuid.UUID, name: str, icon: str | None = None) -> Notebook:
        notebook = Notebook(user_id=user_id, name=name, icon=icon)
        self.session.add(notebook)
        await self.session.flush()
        return notebook

    async def get_by_id(self, notebook_id: uuid.UUID, user_id: uuid.UUID) -> Notebook | None:
        result = await self.session.execute(
            select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> Sequence[Notebook]:
        result = await self.session.execute(
            select(Notebook).where(Notebook.user_id == user_id).order_by(Notebook.created_at.desc())
        )
        return result.scalars().all()

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Notebook).where(Notebook.user_id == user_id)
        )
        return result.scalar_one()

    async def update(self, notebook: Notebook, changes: dict[str, Any]) -> Notebook:
        for field, value in changes.items():
            setattr(notebook, field, value)
        await self.session.flush()
        # updated_at é gerado pelo banco (onupdate), então expira no flush e
        # precisa ser recarregado aqui — fora do contexto async o refresh falha.
        await self.session.refresh(notebook)
        return notebook

    async def delete(self, notebook: Notebook) -> None:
        await self.session.delete(notebook)
        await self.session.flush()
