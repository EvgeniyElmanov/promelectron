"""Helpers для работы с ценами товаров (таблица product_prices).

Единая точка записи цен из всех путей синка 1С и ручного ввода:
- `get_site_price` / `get_site_prices_bulk` — чтение сайтового вида цены
  (в длинных сессиях вместо stale `Product.price` column_property, D-03);
- `upsert_product_price` — upsert по (product_id, price_type) с per-row staleness (D-05).
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.product_price import ProductPrice

logger = logging.getLogger(__name__)


async def get_site_price(
    session: AsyncSession, product_id: int, *, for_update: bool = False
) -> Decimal | None:
    """Сайтовая цена товара или None, если строки сайтового вида нет.

    `for_update=True` блокирует строку product_prices (SELECT ... FOR UPDATE) —
    используется в order path, чтобы снапшот цены читался под блокировкой
    (старая гарантия: цена читалась из заблокированной строки products).
    """
    stmt = select(ProductPrice.price).where(
        ProductPrice.product_id == product_id,
        ProductPrice.price_type == settings.onec_site_price_type,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_site_prices_bulk(
    session: AsyncSession, product_ids: list[int]
) -> dict[int, Decimal]:
    """Сайтовые цены пачкой: {product_id: price} — только по товарам со строкой."""
    if not product_ids:
        return {}
    result = await session.execute(
        select(ProductPrice.product_id, ProductPrice.price).where(
            ProductPrice.product_id.in_(product_ids),
            ProductPrice.price_type == settings.onec_site_price_type,
        )
    )
    return {row.product_id: row.price for row in result.all()}


async def upsert_product_price(
    session: AsyncSession,
    product_id: int,
    price_type: str,
    price: Decimal,
    sync_at: datetime | None = None,
) -> tuple[ProductPrice, bool]:
    """Upsert строки product_prices по (product_id, price_type).

    Per-row staleness: если `sync_at` передан, у строки уже есть `onec_sync_at`
    и `sync_at <= row.onec_sync_at` — запись пропускается.

    Возвращает (row, changed): changed = строка создана или цена изменилась
    (нужен intake loader'у для F007 cache.touched). Обновление onec_sync_at
    само по себе изменением НЕ считается — иначе intake (sync_at=now())
    делал бы changed константно True при каждом reparse (F001).
    """
    result = await session.execute(
        select(ProductPrice).where(
            ProductPrice.product_id == product_id,
            ProductPrice.price_type == price_type,
        )
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = ProductPrice(
            product_id=product_id,
            price_type=price_type,
            price=price,
            onec_sync_at=sync_at,
        )
        session.add(row)
        try:
            # Savepoint: конкурентный upsert той же пары (product_id, price_type)
            # даст UniqueViolation — откатываем только вложенную транзакцию
            # и перечитываем строку конкурента (F009, TOCTOU select-then-insert).
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:
            if row in session:
                session.expunge(row)
            result = await session.execute(
                select(ProductPrice).where(
                    ProductPrice.product_id == product_id,
                    ProductPrice.price_type == price_type,
                )
            )
            row = result.scalar_one()
        else:
            return row, True

    if sync_at is not None and row.onec_sync_at is not None and sync_at <= row.onec_sync_at:
        # F003: skip без записи — логируем, чтобы молчаливая потеря обновлений
        # (расхождение часов intake wall-clock vs 1C version) была наблюдаемой.
        logger.info(
            "Skipping stale price upsert for product_id=%s price_type=%s: "
            "sync_at=%s <= onec_sync_at=%s",
            product_id,
            price_type,
            sync_at,
            row.onec_sync_at,
        )
        return row, False

    changed = row.price != price
    row.price = price
    if sync_at is not None:
        row.onec_sync_at = sync_at
    await session.flush()
    return row, changed
