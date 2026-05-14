from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    text: Optional[str] = None
    is_approved: Optional[bool] = None


class ReviewOut(ReviewBase):
    id: int
    user_id: int
    product_id: int
    is_approved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewWithUser(ReviewOut):
    user_name: Optional[str] = None
