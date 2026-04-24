from pydantic import BaseModel
from typing import List
from decimal import Decimal
from datetime import datetime  # ← Добавь этот импорт

class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    price_at_time: Decimal

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    # Пустой — заказ создаётся из корзины
    pass

class OrderUpdateStatus(BaseModel):
    status: str  # pending, paid, shipped, delivered, cancelled

class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    total_price: Decimal
    created_at: datetime  # ← Теперь datetime известен
    items: List[OrderItemOut]

    class Config:
        from_attributes = True