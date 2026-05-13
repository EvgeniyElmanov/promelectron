from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
