from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import relationship

from src.app.db.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    guest_email = Column(String, nullable=True)
    guest_name = Column(String, nullable=True)
    recipient_first_name = Column(String, nullable=True)
    recipient_last_name = Column(String, nullable=True)
    guest_phone = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)
    total_price = Column(Numeric(precision=10, scale=2), nullable=False)
    shipping_address = Column(JSON, nullable=True)
    tracking_number = Column(String, nullable=True)

    # CDEK delivery fields
    cdek_tariff_code = Column(Integer, nullable=False, default=0)
    cdek_delivery_mode = Column(String, nullable=False, default="PVZ")
    cdek_delivery_point = Column(String, nullable=True)
    cdek_to_location = Column(JSON, nullable=True)
    cdek_from_location = Column(JSON, nullable=True)
    cdek_price = Column(Numeric(precision=10, scale=2), nullable=False, default=0.0)
    cdek_period_min = Column(Integer, nullable=True)
    cdek_period_max = Column(Integer, nullable=True)
    cdek_uuid = Column(String, nullable=True)
    cdek_number = Column(String, nullable=True)
    cdek_status = Column(String, nullable=True)
    cdek_sync_attempts = Column(Integer, nullable=False, default=0)
    cdek_sync_failed = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    user = relationship("User")
    items = relationship("OrderItem", back_populates="order")
    payment = relationship("Payment", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    price_at_time = Column(Numeric(precision=10, scale=2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

