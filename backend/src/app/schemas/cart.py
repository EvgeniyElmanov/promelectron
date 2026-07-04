from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from src.app.schemas.recipient import RecipientOut
from src.app.schemas.user import UserAddressOut


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class CartMergeItem(BaseModel):
    product_id: int
    quantity: int
    selected: bool = True


class CartMergeRequest(BaseModel):
    items: List[CartMergeItem]


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemSelect(BaseModel):
    selected: bool


class CartItemProductOut(BaseModel):
    id: int
    name: str
    price: float
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
    selected: bool
    product: Optional[CartItemProductOut] = None

    model_config = ConfigDict(from_attributes=True)


class CartOut(BaseModel):
    id: int
    user_id: int
    items: List[CartItemOut] = []
    default_recipient: Optional[RecipientOut] = None
    default_address: Optional[UserAddressOut] = None

    model_config = ConfigDict(from_attributes=True)
