import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.auth.dependencies import get_current_user
from src.db.models import User
from src.db.session import get_db
from src.domain.quota import (
    ensure_can_add_file_to_notebook,
    ensure_file_size_allowed,
    ensure_monthly_page_quota,
    ensure_page_count_allowed,
)
from src.errors import AppError
from src.files.repository import FileRepository
from src.files.schemas import FileOut
from src.files.validation import (
    PDF_MIME_TYPE,
    compute_checksum,
    count_pdf_pages,
    ensure_not_empty,
    ensure_pdf_magic_bytes,
    normalize_original_name,
)
from src.notebooks.repository import NotebookRepository
from src.processing.pipeline import ProcessingPipeline, get_pipeline
from src.storage.local import LocalStorage, get_storage, source_key_for

router = APIRouter(prefix="/v1/notebooks/{notebook_id}/files", tags=["files"])


async def _ensure_notebook_owned(db: AsyncSession, notebook_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if await NotebookRepository(db).get_by_id(notebook_id, user_id) is None:
        raise AppError("NOTEBOOK_NOT_FOUND", "Notebook não encontrado.", status.HTTP_404_NOT_FOUND)


def _current_month_start() -> datetime:
    return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.post("", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    notebook_id: uuid.UUID,
    upload: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
    pipeline: ProcessingPipeline = Depends(get_pipeline),
) -> FileOut:
    """Ordem de validação conforme PRD §8 / CLAUDE.md §14: nada pesado acontece
    antes do arquivo passar por todas as verificações."""
    await _ensure_notebook_owned(db, notebook_id, current_user.id)

    original_name = normalize_original_name(upload.filename)

    # Rejeita pelo tamanho anunciado antes de carregar tudo em memória.
    if upload.size is not None:
        ensure_file_size_allowed(current_user.plan, upload.size)

    data = await upload.read()
    ensure_not_empty(data)
    ensure_file_size_allowed(current_user.plan, len(data))

    ensure_pdf_magic_bytes(data)
    page_count = await run_in_threadpool(count_pdf_pages, data)
    ensure_page_count_allowed(current_user.plan, page_count)

    checksum = await run_in_threadpool(compute_checksum, data)

    repository = FileRepository(db)
    ensure_can_add_file_to_notebook(
        current_user.plan, await repository.count_by_notebook(notebook_id, current_user.id)
    )
    ensure_monthly_page_quota(
        current_user.plan,
        await repository.sum_pages_since(current_user.id, _current_month_start()),
        page_count,
    )

    file_id = uuid.uuid4()
    source_key = source_key_for(current_user.id, notebook_id, file_id)

    # A deduplicação é a própria constraint: dois uploads simultâneos passariam
    # por uma consulta prévia, mas só um sobrevive ao insert.
    try:
        file = await repository.create(
            file_id=file_id,
            user_id=current_user.id,
            notebook_id=notebook_id,
            original_name=original_name,
            mime_type=PDF_MIME_TYPE,
            size_bytes=len(data),
            checksum_sha256=checksum,
            page_count=page_count,
            source_key=source_key,
        )
    except IntegrityError as exc:
        raise AppError(
            "FILE_DUPLICATED", "Este arquivo já existe neste notebook.", status.HTTP_409_CONFLICT
        ) from exc

    await run_in_threadpool(storage.save, source_key, data)

    # O background task roda antes do teardown do get_db, então o commit
    # precisa ser explícito: o processamento abre outra sessão e só enxerga o
    # arquivo depois que ele estiver commitado.
    await db.commit()

    # O processamento roda depois da resposta, no mesmo processo (PRD §18: sem
    # Celery/Redis no MVP). O arquivo volta como `pending` e o cliente acompanha
    # o estado pela listagem.
    background_tasks.add_task(pipeline.process, file.id)

    return FileOut.model_validate(file)


@router.get("", response_model=list[FileOut])
async def list_files(
    notebook_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FileOut]:
    await _ensure_notebook_owned(db, notebook_id, current_user.id)

    files = await FileRepository(db).list_by_notebook(notebook_id, current_user.id)
    return [FileOut.model_validate(file) for file in files]
