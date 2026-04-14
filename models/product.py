from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    # Изменили на timezone=True
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Связь с категорией
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    # Связь с поставщиком
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    # Отношения
    category = relationship("Category")  # ← Убран back_populates
    supplier = relationship("Supplier")  # ← Убран back_populates