from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, select
from sqlalchemy.orm import column_property, relationship

from src.app.core.config import settings
from src.app.db.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=True)
    onec_id = Column(String(36), unique=True, index=True, nullable=True)
    onec_sync_at = Column(DateTime(timezone=True), nullable=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    stock = Column(Integer, default=0)
    weight_grams = Column(Integer, nullable=False, default=1000)
    length_cm = Column(Integer, nullable=True)
    width_cm = Column(Integer, nullable=True)
    height_cm = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    images = Column(JSON, default=list, nullable=True)

    category = relationship("Category")
    supplier = relationship("Supplier")


# Импорт в конце модуля — избегаем circular import (product_price ссылается на products.id).
from src.app.models.product_price import ProductPrice  # noqa: E402


def site_price_expression():
    """SQL-выражение сайтовой цены товара (коррелированный скалярный подзапрос).

    Единственное место, где задан фильтр сайтового вида цены
    (settings.onec_site_price_type). Используется в column_property `Product.price`
    и в фильтрах/сортировке каталога.
    """
    return (
        select(ProductPrice.price)
        .where(
            ProductPrice.product_id == Product.id,
            ProductPrice.price_type == settings.onec_site_price_type,
        )
        .scalar_subquery()
    )


# Read-only атрибут: значение фиксируется на момент SELECT.
# В длинных сессиях (onec_intake_loader с инкрементальными upsert'ами цен)
# атрибут будет stale — там цену читать только через price_service.get_site_price.
Product.price = column_property(site_price_expression())
Product.prices = relationship("ProductPrice", cascade="all, delete-orphan")

