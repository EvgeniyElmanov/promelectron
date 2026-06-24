from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CdekLocation(BaseModel):
    code: Optional[int] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None


class CdekStatusHistoryOut(BaseModel):
    id: int
    cdek_status: str
    status_date_time: datetime
    city_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CdekOrderOut(BaseModel):
    id: int
    order_id: Optional[int] = None
    tariff_code: int
    delivery_mode: str
    delivery_point: Optional[str] = None
    to_location: Optional[CdekLocation] = None
    from_location: Optional[CdekLocation] = None
    price: Decimal
    period_min: Optional[int] = None
    period_max: Optional[int] = None
    cdek_uuid: Optional[str] = None
    cdek_number: Optional[str] = None
    cdek_status: Optional[str] = None
    tracking_number: Optional[str] = None
    sync_attempts: int
    sync_failed: bool
    tracking_url: Optional[str] = None
    status_history: list[CdekStatusHistoryOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
