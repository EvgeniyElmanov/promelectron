from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_ORDERS_COLUMNS = [
    "posting_number",
    "order_id",
    "order_number",
    "delivery_schema",
    "status",
    "created_at",
    "in_process_at",
    "sku",
    "offer_id",
    "product_name",
    "quantity",
    "price",
    "currency_code",
    "region",
    "city",
    "delivery_type",
    "commission_amount",
    "commission_percent",
    "payout",
]

_SYNC_KEY = "global"
_ENTITY_TYPE = "orders"
_CHUNK_DAYS = 180  # FBS max ~1 year, use 6 months for safety


def _parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=UTC)
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value
    try:
        text = str(value).rstrip("Z")
        dt = datetime.fromisoformat(text)
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
    except Exception:
        return datetime.fromtimestamp(0, tz=UTC)


def _time_chunks(
    start: datetime, end: datetime, max_days: int
) -> list[tuple[datetime, datetime]]:
    chunks: list[tuple[datetime, datetime]] = []
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=max_days), end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(seconds=1)
    return chunks


def _map_posting_rows(
    posting: dict[str, Any],
    delivery_schema: str,
) -> list[tuple[Any, ...]]:
    posting_number = str(posting.get("posting_number", "") or "")
    order_id = int(posting.get("order_id", 0) or 0)
    order_number = str(posting.get("order_number", "") or "")
    status = str(posting.get("status", "") or "")
    in_process_at = _parse_datetime(posting.get("in_process_at"))
    # FBS has no created_at — use in_process_at or shipment_date as fallback
    created_at = _parse_datetime(
        posting.get("created_at") or posting.get("in_process_at") or posting.get("shipment_date")
    )

    analytics: dict[str, Any] = posting.get("analytics_data") or {}
    region = str(analytics.get("region", "") or "")
    city = str(analytics.get("city", "") or "")
    delivery_type = str(analytics.get("delivery_type", "") or "")

    fin_products: list[dict[str, Any]] = (
        (posting.get("financial_data") or {}).get("products") or []
    )
    fin_by_product_id: dict[int, dict[str, Any]] = {
        int(p.get("product_id", 0)): p for p in fin_products
    }

    products: list[dict[str, Any]] = posting.get("products") or []
    rows: list[tuple[Any, ...]] = []
    for product in products:
        sku = int(product.get("sku", 0) or 0)
        offer_id = str(product.get("offer_id", "") or "")
        product_name = str(product.get("name", "") or "")
        quantity = int(product.get("quantity", 0) or 0)
        price = _parse_decimal(product.get("price", "0"))
        currency_code = str(product.get("currency_code", "") or "")

        fin = fin_by_product_id.get(sku, {})
        commission_amount = _parse_decimal(fin.get("commission_amount", "0"))
        commission_percent = float(fin.get("commission_percent", 0) or 0)
        payout = _parse_decimal(fin.get("payout", "0"))

        rows.append((
            posting_number,
            order_id,
            order_number,
            delivery_schema,
            status,
            created_at,
            in_process_at,
            sku,
            offer_id,
            product_name,
            quantity,
            price,
            currency_code,
            region,
            city,
            delivery_type,
            commission_amount,
            commission_percent,
            payout,
        ))

    return rows


async def sync_orders(
    ozon: OzonClient,
    ch: ClickHouseClient,
    *,
    since: str | None = None,
    full: bool = False,
) -> None:
    now = datetime.now(UTC)

    if since:
        since_dt = datetime.fromisoformat(since).replace(tzinfo=UTC)
    elif full:
        since_dt = now - timedelta(days=365 * 3)
    else:
        checkpoint = ch.get_checkpoint(_SYNC_KEY, _ENTITY_TYPE)
        since_dt = checkpoint - timedelta(hours=1) if checkpoint else now - timedelta(days=365 * 3)

    chunks = _time_chunks(since_dt, now, _CHUNK_DAYS)
    logger.info(
        "Syncing orders from %s to %s (%d chunk(s))",
        since_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        len(chunks),
    )

    all_rows: list[tuple[Any, ...]] = []
    total_fbo = 0
    total_fbs = 0

    for chunk_start, chunk_end in chunks:
        s = chunk_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        e = chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        # FBO orders (no period limit known, but chunk anyway)
        async for page in await ozon.get_fbo_orders(s, e):
            for posting in page:
                all_rows.extend(_map_posting_rows(posting, "FBO"))
            total_fbo += len(page)

        # FBS orders (max ~1 year per request)
        async for page in await ozon.get_fbs_orders(s, e):
            for posting in page:
                all_rows.extend(_map_posting_rows(posting, "FBS"))
            total_fbs += len(page)

        logger.info("Chunk %s..%s: FBO=%d, FBS=%d", s, e, total_fbo, total_fbs)

    logger.info("Total: FBO %d + FBS %d postings -> %d rows", total_fbo, total_fbs, len(all_rows))

    if not all_rows:
        logger.info("No order rows to insert")
        ch.save_checkpoint(_SYNC_KEY, _ENTITY_TYPE, now, 0)
        return

    ch.insert_rows("orders", _ORDERS_COLUMNS, all_rows)

    ch.save_checkpoint(_SYNC_KEY, _ENTITY_TYPE, now, len(all_rows))
    logger.info("Orders sync complete: %d total rows inserted", len(all_rows))
