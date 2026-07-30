"""Модели SQLAlchemy виртуального каталога 1С и журналов (схема onec_mock, D-03/D-04).

Изолированная схема, без Alembic и без FK в public: создание на старте сервиса.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from onec_mock.config import settings


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _guid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    metadata = MetaData(schema=settings.onec_mock_schema)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    onec_id: Mapped[str] = mapped_column(String(36), unique=True, default=_guid)
    name: Mapped[str] = mapped_column(String(255))
    parent_onec_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Attribute(Base):
    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    value_type: Mapped[str] = mapped_column(String(32))  # 'number' | 'text'
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    onec_id: Mapped[str] = mapped_column(String(36), default=_guid)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    onec_id: Mapped[str] = mapped_column(String(36), unique=True, default=_guid)
    sku: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    # Осознанно без FK на categories.onec_id (F009): схема мока — плоская симуляция
    # каталога 1С, ссылочная целостность не нужна и усложняет seed/мутации
    category_onec_id: Mapped[str] = mapped_column(String(36))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ProductAttributeValue(Base):
    __tablename__ = "product_attribute_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"))
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(512), nullable=True)


class ChangeLog(Base):
    """Журнал зарегистрированных изменений (план обмена 1С, D-04)."""

    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))  # product|category|price|stock|attribute
    entity_onec_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(16))  # create|update|delete
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SentChanges(Base):
    """Журнал попыток отправки пакетов (D-07)."""

    __tablename__ = "sent_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)  # обрезанный ~2KB
    checksum: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16))  # success|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Байты пакета последней отправки — нужны сценарию duplicate_batch (D-06)
    package_zip: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class ScenarioRun(Base):
    """Журнал запусков сценариев мутаций (D-06)."""

    __tablename__ = "scenario_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    changes_created: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running|success|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
