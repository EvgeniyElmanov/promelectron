from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from src.app.db.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    status = Column(String, default="pending", nullable=False)
    provider_payment_id = Column(String, nullable=True)

    # YooKassa fields
    yookassa_payment_id = Column(String, nullable=True, unique=True)
    yookassa_status = Column(String, nullable=True)
    confirmation_url = Column(String, nullable=True)
    payment_method_type = Column(String, nullable=True)
    refunded_amount = Column(Numeric(precision=10, scale=2), nullable=True, default=0)
    yookassa_metadata = Column(JSON, nullable=True)
    yookassa_created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    paid_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="payment")
