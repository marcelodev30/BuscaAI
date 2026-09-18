import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.auth.dependencies import get_current_user
from src.db.models import Notebook, User
from src.db.session import get_db
from src.domain.quota import ensure_can_create_notebook
from src.errors import AppError
from src.notebooks.repository import NotebookRepository
from src.notebooks.schemas import CreateNotebookRequest, NotebookOut, UpdateNotebookRequest
from src.storage.local import LocalStorage, get_storage, notebook_prefix_for

router = APIRouter(prefix="/v1/notebooks", tags=["notebooks"])


async def _get_owned_notebook(
    repository: NotebookRepository, notebook_id: uuid.UUID, user_id: uuid.UUID
) -> Notebook:
    notebook = await repository.get_by_id(notebook_id, user_id)
    if notebook is None:
        raise AppError("NOTEBOOK_NOT_FOUND", "Notebook não encontrado.", status.HTTP_404_NOT_FOUND)
    return notebook


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    payload: CreateNotebookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotebookOut:
    repository = NotebookRepository(db)

    ensure_can_create_notebook(current_user.plan, await repository.count_by_user(current_user.id))

    notebook = await repository.create(user_id=current_user.id, name=payload.name, icon=payload.icon)
    return NotebookOut.model_validate(notebook)


@router.get("", response_model=list[NotebookOut])
async def list_notebooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotebookOut]:
    notebooks = await NotebookRepository(db).list_by_user(current_user.id)
    return [NotebookOut.model_validate(notebook) for notebook in notebooks]


@router.get("/{notebook_id}", response_model=NotebookOut)
async def get_notebook(
    notebook_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotebookOut:
    notebook = await _get_owned_notebook(NotebookRepository(db), notebook_id, current_user.id)
    return NotebookOut.model_validate(notebook)


@router.patch("/{notebook_id}", response_model=NotebookOut)
async def update_notebook(
    notebook_id: uuid.UUID,
    payload: UpdateNotebookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotebookOut:
    repository = NotebookRepository(db)
    notebook = await _get_owned_notebook(repository, notebook_id, current_user.id)

    await repository.update(notebook, payload.model_dump(exclude_unset=True))
    return NotebookOut.model_validate(notebook)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> None:
    repository = NotebookRepository(db)
    notebook = await _get_owned_notebook(repository, notebook_id, current_user.id)

    # As linhas de files somem por cascade; os PDFs no disco precisam ser
    # apagados aqui, senão ficam órfãos.
    await repository.delete(notebook)
    await run_in_threadpool(storage.delete_prefix, notebook_prefix_for(current_user.id, notebook_id))
