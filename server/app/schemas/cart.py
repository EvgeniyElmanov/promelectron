from typing import List

from pydantic import BaseModel, ConfigDict


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class CartOut(BaseModel):
    id: int
    user_id: int
    items: List[CartItemOut] = []

    model_config = ConfigDict(from_attributes=True)
