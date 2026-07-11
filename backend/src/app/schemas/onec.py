from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OnecChange(BaseModel):
    external_id: str
    action: Literal["create", "update", "delete"]
    version: datetime
    data: dict[str, Any]


class OnecWebhookPayload(BaseModel):
    batch_id: UUID
    sent_at: datetime
    base_name: str
    entity_type: Literal["product", "category"]
    changes: list[OnecChange]


class OnecWebhookResponse(BaseModel):
    status: str
    batch_id: UUID

    model_config = ConfigDict(from_attributes=True)
