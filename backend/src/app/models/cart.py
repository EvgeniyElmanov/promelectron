from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.types import DateTime

from src.app.db.database import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    items = relationship("CartItem", back_populates="cart")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    # D-01: колонка уже создана миграцией 9614c59dd5a3 (середина цепочки) —
    # модель догоняет миграцию, новая миграция не нужна.
    selected = Column(Boolean, nullable=False, default=True, server_default=sa.true())

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

