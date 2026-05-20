from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeliveryMethodBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: float = 0.0
    estimated_days: Optional[str] = None
    is_active: bool = True


class DeliveryMethodCreate(DeliveryMethodBase):
    pass


class DeliveryMethodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    estimated_days: Optional[str] = None
    is_active: Optional[bool] = None


class DeliveryMethodOut(DeliveryMethodBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
