from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryOut(CategoryBase):
    id: int
    is_active: bool
    created_at: datetime
    product_count: int = 0
    # Первое изображение активного товара категории (заполняется в list-эндпоинте)
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryListOut(BaseModel):
    items: list[CategoryOut]
    total: int
