from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    price_at_time: Decimal

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    pass

    class Config:
        from_attributes = True


class OrderUpdateStatus(BaseModel):
    status: str


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    total_price: Decimal
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True

