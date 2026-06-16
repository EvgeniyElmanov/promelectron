from typing import Optional

from pydantic import BaseModel, ConfigDict


class SupplierOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    cdek_shipment_point: str
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SupplierUpdate(BaseModel):
    cdek_shipment_point: Optional[str] = None
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
