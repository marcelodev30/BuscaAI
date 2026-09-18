import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.file_state import FileStatus


class FileOut(BaseModel):
    """error_message não é exposto: o usuário recebe o código, os detalhes
    técnicos ficam para a operação (PRD §9)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notebook_id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    status: FileStatus
    stage: str | None
    progress: int
    page_count: int | None
    chunk_count: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
