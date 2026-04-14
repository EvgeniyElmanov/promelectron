from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    # Изменили на timezone=True
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Отношения
    parent = relationship("Category", remote_side=[id])
    # products = relationship("Product", back_populates="category")  # ← Убрали