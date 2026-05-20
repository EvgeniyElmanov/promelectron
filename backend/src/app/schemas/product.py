from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from src.app.schemas.review import ReviewOut


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    is_active: bool = True
    category_id: Optional[int] = None
    images: List[str] = []


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    supplier_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductDetailOut(ProductOut):
    reviews: List[ReviewOut] = []
    average_rating: float = 0.0
    reviews_count: int = 0
    is_favorite: bool = False


class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
