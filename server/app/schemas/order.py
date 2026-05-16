from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    price_at_time: Decimal

    model_config = ConfigDict(from_attributes=True)


class AddressDetails(BaseModel):
    region: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    apartment: Optional[str] = None


class OrderCreate(BaseModel):
    shipping_address: Optional[AddressDetails] = None

    model_config = ConfigDict(from_attributes=True)


class OrderUpdateStatus(BaseModel):
    status: str


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    total_price: Decimal
    shipping_address: Optional[str] = None
    created_at: datetime
    items: List[OrderItemOut]

    model_config = ConfigDict(from_attributes=True)
