from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PaymentOut(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: str
    provider_payment_id: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentCreateResponse(BaseModel):
    payment_id: int
    status: str
    confirmation_url: str
    amount: Decimal
