"""Агрегаты карточки товара для list-ответов (pixel-perfect-homepage, D-03).

Общий хелпер для ``ProductService.read_products`` и обогащения поисковых hits
(``search_query.search_products``): рейтинг/отзывы/бренд/хиты загружаются
батчами по ``product_ids`` — без N+1.

Правила:
- ``average_rating``/``reviews_count`` — только одобренные отзывы
  (``Review.is_approved``), округление до 1 знака, как в detail.
- ``brand`` — ``value_text`` атрибута с именем «Бренд» (в данных 1С ``code``
  атрибута — GUID, поэтому матч по name), резолв как в detail.
- ``is_hit`` — простое правило: ≥1 позиция в оплаченных заказах
  (``Order.status == "paid"``) за последние 90 дней.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.attribute import Attribute, ProductAttributeValue
from src.app.models.order import Order, OrderItem
from src.app.models.review import Review

BRAND_ATTRIBUTE_NAME = "Бренд"
HIT_WINDOW_DAYS = 90


async def load_product_list_aggregates(
    db: AsyncSession,
    product_ids: list[int],
    brand_ids: list[int] | None = None,
) -> dict[int, dict[str, Any]]:
    """Загрузить агрегаты карточки для набора товаров батч-запросами.

    ``brand_ids`` — подмножество ``product_ids``, для которого нужен бренд
    (brand-запрос к БД пропускается, если список пуст); ``None`` (дефолт) —
    бренд грузится для всех ``product_ids``. Поиск передаёт только hits
    без brand в документе Meilisearch (review F-02).

    Returns ``{product_id: {"average_rating": float, "reviews_count": int,
    "brand": str | None, "is_hit": bool}}``; товары без данных отсутствуют
    в результате (вызывающий код подставляет дефолты схемы).
    """
    ids = sorted({int(pid) for pid in product_ids})
    if not ids:
        return {}

    aggregates: dict[int, dict[str, Any]] = {}

    rating_result = await db.execute(
        select(
            Review.product_id,
            func.avg(Review.rating),
            func.count(Review.id),
        )
        .where(Review.product_id.in_(ids), Review.is_approved.is_(True))
        .group_by(Review.product_id)
    )
    for product_id, avg, count in rating_result.all():
        entry = aggregates.setdefault(product_id, {})
        entry["average_rating"] = round(float(avg), 1) if avg else 0.0
        entry["reviews_count"] = int(count)

    brand_query_ids = ids if brand_ids is None else sorted({int(pid) for pid in brand_ids})
    if brand_query_ids:
        brand_result = await db.execute(
            select(ProductAttributeValue.product_id, ProductAttributeValue.value_text)
            .join(Attribute, ProductAttributeValue.attribute_id == Attribute.id)
            .where(
                ProductAttributeValue.product_id.in_(brand_query_ids),
                Attribute.name == BRAND_ATTRIBUTE_NAME,
                ProductAttributeValue.value_text.isnot(None),
            )
        )
        for product_id, value_text in brand_result.all():
            aggregates.setdefault(product_id, {})["brand"] = value_text

    hit_threshold = datetime.now(timezone.utc) - timedelta(days=HIT_WINDOW_DAYS)
    hit_result = await db.execute(
        select(OrderItem.product_id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            OrderItem.product_id.in_(ids),
            Order.status == "paid",
            Order.created_at >= hit_threshold,
        )
        .distinct()
    )
    for (product_id,) in hit_result.all():
        aggregates.setdefault(product_id, {})["is_hit"] = True

    return aggregates
