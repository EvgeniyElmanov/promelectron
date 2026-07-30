from datetime import datetime
from decimal import Decimal
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
    entity_type: Literal["product", "category", "price", "stock", "order_status"]
    changes: list[OnecChange]


class OnecWebhookResponse(BaseModel):
    status: str
    batch_id: UUID

    model_config = ConfigDict(from_attributes=True)


class OnecIntakeResponse(BaseModel):
    intake_id: UUID
    received_bytes: int


# ─── OData-сущности 1С:УНФ (pull fallback) ───────────────────────────────────


class OnecCategoryOdata(BaseModel):
    """Catalog_КатегорииНоменклатуры."""

    ref_key: str
    parent_key: str | None
    description: str


class OnecProductOdata(BaseModel):
    """Catalog_Номенклатура (фильтр: ТипНоменклатуры eq 'Запас' and IsFolder eq false)."""

    ref_key: str
    description: str
    article: str | None
    code: str | None
    parent_key: str | None
    is_folder: bool
    item_type: str


class OnecPriceOdata(BaseModel):
    """InformationRegister_ЦеныНоменклатуры."""

    product_key: str
    price_type_key: str
    price: Decimal


class OnecStockOdata(BaseModel):
    """AccumulationRegister_ЗапасыНаСкладах/Balance."""

    product_key: str
    warehouse_key: str | None
    quantity: int
