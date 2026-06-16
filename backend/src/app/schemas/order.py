from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class CdekLocation(BaseModel):
    code: Optional[int] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None


class CdekDeliveryIn(BaseModel):
    tariff_code: int
    delivery_mode: str = Field(..., pattern="^(PVZ|DOOR)$")
    delivery_point: Optional[str] = None
    to_location: Optional[CdekLocation] = None
    from_location: Optional[CdekLocation] = None
    price: Decimal
    period_min: Optional[int] = None
    period_max: Optional[int] = None
    shipping_address: Optional[str] = None


class OrderCreate(BaseModel):
    cdek_delivery: CdekDeliveryIn

    model_config = ConfigDict(from_attributes=True)


class GuestOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class GuestOrderCreate(BaseModel):
    items: List[GuestOrderItemCreate]
    cdek_delivery: CdekDeliveryIn
    guest_email: str
    guest_name: str
    guest_phone: str

    model_config = ConfigDict(from_attributes=True)


class OrderUpdateStatus(BaseModel):
    status: str


class AdminOrderUpdate(BaseModel):
    status: Optional[str] = None
    tracking_number: Optional[str] = None


class SupplierOrderItemOut(BaseModel):
    product_name: str
    quantity: int
    price_per_item: Decimal

    model_config = ConfigDict(from_attributes=True)


class SupplierOrderOut(BaseModel):
    id: int
    buyer_name: Optional[str] = None
    buyer_email: str
    total_amount: Decimal
    status: str
    created_at: datetime
    items: List[SupplierOrderItemOut]

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    status: str
    total_price: Decimal
    shipping_address: Optional[str] = None
    guest_email: Optional[str] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    created_at: datetime
    items: List[OrderItemOut]
    tracking_number: Optional[str] = None

    # CDEK fields
    cdek_tariff_code: int
    cdek_delivery_mode: str
    cdek_delivery_point: Optional[str] = None
    cdek_to_location: Optional[CdekLocation] = None
    cdek_from_location: Optional[CdekLocation] = None
    cdek_price: Decimal
    cdek_period_min: Optional[int] = None
    cdek_period_max: Optional[int] = None
    cdek_uuid: Optional[str] = None
    cdek_number: Optional[str] = None
    cdek_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
