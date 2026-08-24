from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.app.models.attribute import AttributeValueType
from src.app.schemas.review import ReviewOut


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    # Сайтовая цена: None — у товара нет строки сайтового вида в product_prices
    price: Optional[Decimal] = None
    stock: int = 0
    weight_grams: int = 1000
    length_cm: Optional[int] = None
    width_cm: Optional[int] = None
    height_cm: Optional[int] = None
    is_active: bool = True
    category_id: Optional[int] = None
    images: List[str] = []

    @field_serializer("price")
    def serialize_price(self, value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None


class ProductCreate(ProductBase):
    # При создании цена обязательна и > 0 (B-01); пишется сайтовой строкой (D-13)
    price: Decimal = Field(gt=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = None
    weight_grams: Optional[int] = None
    length_cm: Optional[int] = None
    width_cm: Optional[int] = None
    height_cm: Optional[int] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = None
    images: Optional[List[str]] = None


class ProductAttributeValueOut(BaseModel):
    """Типизированное значение характеристики товара в detail-ответе (D-02)."""

    code: str
    name: str
    value_type: AttributeValueType
    value: float | bool | str
    unit: Optional[str] = None


class ProductOut(ProductBase):
    id: int
    sku: Optional[str] = None
    supplier_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductDetailOut(ProductOut):
    attributes: List[ProductAttributeValueOut] = []
    reviews: List[ReviewOut] = []
    average_rating: float = 0.0
    reviews_count: int = 0
    is_favorite: bool = False


class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
