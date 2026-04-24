from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import DateTime
from datetime import datetime, timezone
from database import Base

class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Отношение: корзина → пользователь
    user = relationship("User")
    # Отношение: корзина → элементы корзины
    items = relationship("CartItem", back_populates="cart")  # ← Добавь это

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)

    # Отношения
    cart = relationship("Cart", back_populates="items")  # ← Убедись, что это есть
    product = relationship("Product")