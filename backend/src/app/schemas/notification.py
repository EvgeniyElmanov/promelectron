from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    order_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationList(BaseModel):
    items: List[NotificationOut]
    unread_count: int
