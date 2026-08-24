from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class CartMergeRequest(BaseModel):
    items: List[CartItemCreate]


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemProductOut(BaseModel):
    id: int
    name: str
    price: Optional[float] = None
    stock: int
    supplier_id: int
    weight_grams: int
    length_cm: Optional[int] = None
    width_cm: Optional[int] = None
    height_cm: Optional[int] = None
    images: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: Optional[CartItemProductOut] = None

    model_config = ConfigDict(from_attributes=True)


class CartOut(BaseModel):
    id: int
    user_id: int
    items: List[CartItemOut] = []

    model_config = ConfigDict(from_attributes=True)
