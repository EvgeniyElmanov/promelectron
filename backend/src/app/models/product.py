from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

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
    price = Column(Numeric(precision=10, scale=2), nullable=False)
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

