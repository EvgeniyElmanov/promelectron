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
    entity_type: Literal[
        "product",
        "category",
        "price",
        "stock",
        "order_status",
        "product_attributes",
        "product_images",
    ]
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
    deletion_mark: bool = False


class OnecProductOdata(BaseModel):
    """Catalog_Номенклатура (фильтр: ТипНоменклатуры eq 'Запас' and IsFolder eq false)."""

    ref_key: str
    description: str
    full_name: str | None = None
    article: str | None
    code: str | None
    parent_key: str | None
    category_key: str | None = None
    is_folder: bool
    item_type: str
    weight_grams: int = 1000
    deletion_mark: bool = False


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


class OnecAttributeDefinitionOdata(BaseModel):
    """ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения."""

    ref_key: str
    name: str
    value_type: str | None = None
    deletion_mark: bool = False


class OnecAttributeValueOdata(BaseModel):
    """Catalog_ЗначенияСвойствОбъектов (справочник enum-значений свойств)."""

    ref_key: str
    description: str
    owner_key: str | None = None
    deletion_mark: bool = False


class OnecProductAttributeOdata(BaseModel):
    """Catalog_Номенклатура_ДополнительныеРеквизиты (строка ТЧ товара)."""

    product_key: str
    line_number: str | None = None
    attribute_key: str
    value_key: str | None = None
    text_value: str | None = None
    value_type_name: str | None = None


class OnecProductFileOdata(BaseModel):
    """Catalog_НоменклатураПрисоединенныеФайлы (метаданные файла-изображения)."""

    ref_key: str
    description: str
    product_key: str
    extension: str = "jpg"
    deletion_mark: bool = False
