import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

NotebookName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
NotebookIcon = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]


class CreateNotebookRequest(BaseModel):
    name: NotebookName
    icon: NotebookIcon | None = None


class UpdateNotebookRequest(BaseModel):
    """Campos omitidos ficam inalterados. `icon` aceita null para limpar o
    ícone; `name` não, porque é obrigatório (PRD §7)."""

    name: NotebookName | None = None
    icon: NotebookIcon | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and "name" in data and data["name"] is None:
            raise ValueError("O nome do notebook não pode ser nulo.")
        return data


class NotebookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    icon: str | None
    created_at: datetime
    updated_at: datetime
