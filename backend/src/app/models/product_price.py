from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint

from src.app.db.database import Base


class ProductPrice(Base):
    """Цена товара по виду цен 1С (price_type — строка «как прислала 1С»: GUID или CML-ид).

    Источник истины для всех видов цен (сайтовая, себестоимость и т.д.).
    Сайтовый вид цены задаётся настройкой ONEC_SITE_PRICE_TYPE.
    """

    __tablename__ = "product_prices"
    __table_args__ = (
        UniqueConstraint("product_id", "price_type", name="uq_product_prices_product_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    price_type = Column(String(64), nullable=False)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="RUB")
    onec_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
