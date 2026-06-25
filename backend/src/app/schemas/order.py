from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.app.schemas.cdek_order import CdekLocation, CdekOrderOut
from src.app.schemas.recipient import CountryCode, RecipientOut


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


class CdekDeliveryIn(BaseModel):
    tariff_code: int
    tariff_name: Optional[str] = None
    delivery_mode: str = Field(..., pattern="^(PVZ|DOOR)$")
    delivery_point: Optional[str] = None
    to_location: Optional[CdekLocation] = None
    from_location: Optional[CdekLocation] = None
    price: Decimal
    period_min: Optional[int] = None
    period_max: Optional[int] = None
    shipping_address: Optional[str] = None


def _normalize_recipient_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value


class OrderCreate(BaseModel):
    cdek_delivery: CdekDeliveryIn
    recipient_id: Optional[int] = None
    recipient_first_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    recipient_last_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    recipient_patronymic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    recipient_phone: Optional[str] = Field(default=None, pattern=r'^\+7\d{10}$')
    recipient_country_code: CountryCode = Field(default="RU")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @field_validator("recipient_first_name", "recipient_last_name", "recipient_patronymic", mode="before")
    @classmethod
    def normalize_recipient_name(cls, value):
        return _normalize_recipient_name(value)

    @model_validator(mode="after")
    def check_recipient_data(self):
        if self.recipient_id is not None:
            return self
        if not self.recipient_first_name or not self.recipient_last_name or not self.recipient_phone:
            raise ValueError("Either recipient_id or recipient first_name/last_name/phone must be provided")
        return self


class GuestOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class GuestOrderCreate(BaseModel):
    items: List[GuestOrderItemCreate]
    cdek_delivery: CdekDeliveryIn
    guest_email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    guest_name: Optional[str] = None
    recipient_first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    recipient_last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    recipient_patronymic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    recipient_phone: str = Field(..., pattern=r'^\+7\d{10}$')
    recipient_country_code: CountryCode = Field(default="RU")
    save_address: bool = False

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @field_validator("recipient_first_name", "recipient_last_name", "recipient_patronymic", mode="before")
    @classmethod
    def normalize_recipient_name(cls, value):
        return _normalize_recipient_name(value)


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
    recipient_first_name: Optional[str] = None
    recipient_last_name: Optional[str] = None
    guest_phone: Optional[str] = None
    created_at: datetime
    items: List[OrderItemOut]
    tracking_number: Optional[str] = None
    cdek_order: Optional[CdekOrderOut] = None
    save_address: bool = False
    cancelled_at: Optional[datetime] = None
    recipient: Optional[RecipientOut] = None

    model_config = ConfigDict(from_attributes=True)
