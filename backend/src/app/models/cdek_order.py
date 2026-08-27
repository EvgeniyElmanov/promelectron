from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.app.db.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CdekOrder(Base):
    __tablename__ = "cdek_orders"
    __table_args__ = (
        UniqueConstraint("order_id", name="cdek_orders_order_id_key"),
        UniqueConstraint("cdek_uuid", name="cdek_orders_cdek_uuid_key"),
    )

    id = Column(Integer, primary_key=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Delivery selection snapshot
    tariff_code = Column(Integer, nullable=False, default=0)
    delivery_mode = Column(String, nullable=False, default="PVZ")
    delivery_point = Column(String, nullable=True)
    to_location = Column(JSONB, nullable=True)
    from_location = Column(JSONB, nullable=True)
    price = Column(Numeric(precision=10, scale=2), nullable=False, default=0.0)
    period_min = Column(Integer, nullable=True)
    period_max = Column(Integer, nullable=True)

    # CDEK API state
    cdek_uuid = Column(String, nullable=True, index=True)
    cdek_number = Column(String, nullable=True, index=True)
    cdek_status = Column(String, nullable=True, index=True)
    tracking_number = Column(String, nullable=True)
    sync_attempts = Column(Integer, nullable=False, default=0)
    sync_failed = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )

    order = relationship("Order", back_populates="cdek_order", foreign_keys=[order_id])
    status_history = relationship(
        "CdekStatusHistory",
        back_populates="cdek_order",
        cascade="all, delete-orphan",
        order_by="CdekStatusHistory.status_date_time.desc()",
    )

    @property
    def tracking_url(self) -> str | None:
        """Public CDEK tracking URL."""
        identifier = self.cdek_number or self.tracking_number or self.cdek_uuid
        if not identifier:
            return None
        return f"https://www.cdek.ru/ru/tracking?order_id={identifier}"


class CdekStatusHistory(Base):
    __tablename__ = "cdek_status_history"

    __table_args__ = (
        UniqueConstraint("cdek_order_id", "cdek_status", "status_date_time"),
    )

    id = Column(Integer, primary_key=True)
    cdek_order_id = Column(
        Integer,
        ForeignKey("cdek_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cdek_status = Column(String, nullable=False, index=True)
    status_date_time = Column(DateTime(timezone=True), nullable=False, index=True)
    city_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    cdek_order = relationship("CdekOrder", back_populates="status_history")
