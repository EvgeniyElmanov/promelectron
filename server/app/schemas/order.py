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
    delivery_method_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class OrderUpdateStatus(BaseModel):
    status: str


class AdminOrderUpdate(BaseModel):
    status: Optional[str] = None
    tracking_number: Optional[str] = None


class DeliveryMethodOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    base_price: float
    estimated_days: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    total_price: Decimal
    delivery_method_id: Optional[int] = None
    delivery_price: Optional[Decimal] = None
    shipping_address: Optional[str] = None
    created_at: datetime
    items: List[OrderItemOut]
    tracking_number: Optional[str] = None
    delivery_method: Optional[DeliveryMethodOut] = None

    model_config = ConfigDict(from_attributes=True)
