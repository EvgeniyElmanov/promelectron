from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.app.db.database import Base


class AttributeValueType(PyEnum):
    """Тип значения атрибута товара (D-01, Фаза 4 #120)."""

    number = "number"
    enum = "enum"
    bool = "bool"
    string = "string"


class Attribute(Base):
    """Справочник характеристик товаров (мастер — 1С, auto-create по code).

    Админ Promelectron управляет только отображением (is_filterable, name,
    sort); значения — в ProductAttributeValue (typed-колонки, D-01).
    """

    __tablename__ = "attributes"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    value_type = Column(
        Enum(AttributeValueType), nullable=False, default=AttributeValueType.string
    )
    unit = Column(String, nullable=True)
    is_filterable = Column(Boolean, nullable=False, default=False)
    sort = Column(Integer, nullable=False, default=0)
    onec_id = Column(String(36), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    values = relationship("ProductAttributeValue", back_populates="attribute")


class ProductAttributeValue(Base):
    """Типизированное значение характеристики товара (D-01, D-10).

    Ровно одна из колонок value_number/value_text/value_bool заполнена
    в соответствии с Attribute.value_type. option_id зарезервирован под
    таблицу attribute_options (out of scope Фазы 4, FK не создаётся).
    """

    __tablename__ = "product_attribute_values"
    __table_args__ = (
        UniqueConstraint("product_id", "attribute_id", name="uq_product_attribute"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    attribute_id = Column(Integer, ForeignKey("attributes.id"), nullable=False, index=True)
    value_number = Column(Numeric(precision=18, scale=6), nullable=True)
    value_text = Column(String, nullable=True)
    value_bool = Column(Boolean, nullable=True)
    option_id = Column(Integer, nullable=True)

    product = relationship("Product")
    attribute = relationship("Attribute", back_populates="values")
