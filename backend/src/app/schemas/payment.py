from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class PaymentOut(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: str
    provider_payment_id: Optional[str] = None
    yookassa_payment_id: Optional[str] = None
    yookassa_status: Optional[str] = None
    confirmation_url: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentCreateResponse(BaseModel):
    payment_id: int
    status: str
    confirmation_url: Optional[str] = None
    amount: Decimal


class PaymentDebugSetStatusRequest(BaseModel):
    order_id: int
    status: Literal["succeeded", "canceled"]
    cancellation_reason: Optional[str] = None
    guest_email: Optional[str] = None

    @model_validator(mode="after")
    def require_cancellation_reason_for_canceled(self):
        if self.status == "canceled" and not self.cancellation_reason:
            raise ValueError("cancellation_reason is required when status is canceled")
        return self
