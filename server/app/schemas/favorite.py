from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from server.app.schemas.product import ProductOut


class FavoriteCreate(BaseModel):
    product_id: int


class FavoriteOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavoriteWithProduct(FavoriteOut):
    product: Optional[ProductOut] = None
