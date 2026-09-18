import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NotebookName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
NotebookIcon = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]


class CreateNotebookRequest(BaseModel):
    name: NotebookName
    icon: NotebookIcon | None = None


class UpdateNotebookRequest(BaseModel):
    name: NotebookName | None = None
    icon: NotebookIcon | None = None


class NotebookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    icon: str | None
    created_at: datetime
    updated_at: datetime
