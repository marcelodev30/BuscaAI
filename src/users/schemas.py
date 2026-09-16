import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.db.models import UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    avatar_url: str | None
    status: UserStatus
    plan: str
    created_at: datetime
