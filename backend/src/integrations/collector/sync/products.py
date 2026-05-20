from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_PRODUCTS_COLUMNS = [
    "product_id",
    "offer_id",
    "name",
    "barcode",
    "marketing_price",
    "min_price",
    "old_price",
    "price",
    "currency_code",
    "vat",
    "fbo_present",
    "fbo_reserved",
    "fbs_present",
    "fbs_reserved",
    "visible",
    "status",
    "archived",
    "images",
    "primary_image",
    "volume_weight",
    "is_kgt",
    "created_at",
    "updated_at",
    "description_category_id",
    "type_id",
]

_SYNC_KEY = "global"
_ENTITY_TYPE = "products"


def _parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    try:
        text = str(value).rstrip("Z")
        dt = datetime.fromisoformat(text)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _extract_stock(stocks: list[dict[str, Any]], source: str) -> tuple[int, int]:
    for stock in stocks:
        if stock.get("source") == source:
            return int(stock.get("present", 0)), int(stock.get("reserved", 0))
    return 0, 0


def _map_product(raw: dict[str, Any]) -> tuple[Any, ...]:
    stocks: list[dict[str, Any]] = raw.get("stocks", {}).get("stocks", []) or []
    fbo_present, fbo_reserved = _extract_stock(stocks, "fbo")
    fbs_present, fbs_reserved = _extract_stock(stocks, "fbs")

    images: list[str] = raw.get("images", []) or []

    # primary_image can be a list ["url"] or a string
    raw_primary = raw.get("primary_image", "") or ""
    if isinstance(raw_primary, list):
        primary_image = raw_primary[0] if raw_primary else ""
    else:
        primary_image = str(raw_primary)
    if not primary_image and images:
        primary_image = images[0]

    statuses: dict[str, Any] = raw.get("statuses", {}) or {}
    status: str = statuses.get("status", "") or ""

    barcodes: list[str] = raw.get("barcodes", []) or []
    barcode = barcodes[0] if barcodes else ""

    visibility = raw.get("visibility_details", {}) or {}
    visible = int(visibility.get("has_price", False) and visibility.get("has_stock", False))

    return (
        int(raw.get("id", 0)),
        str(raw.get("offer_id", "") or ""),
        str(raw.get("name", "") or ""),
        barcode,
        _parse_decimal(raw.get("marketing_price", "0")),
        _parse_decimal(raw.get("min_price", "0")),
        _parse_decimal(raw.get("old_price", "0")),
        _parse_decimal(raw.get("price", "0")),
        str(raw.get("currency_code", "") or ""),
        str(raw.get("vat", "") or ""),
        fbo_present,
        fbo_reserved,
        fbs_present,
        fbs_reserved,
        visible,
        status,
        int(bool(raw.get("is_archived", False))),
        images,
        primary_image,
        float(raw.get("volume_weight", 0) or 0),
        int(bool(raw.get("is_kgt", False))),
        _parse_datetime(raw.get("created_at")),
        _parse_datetime(raw.get("updated_at")),
        int(raw.get("description_category_id", 0) or 0),
        int(raw.get("type_id", 0) or 0),
    )


async def sync_products(ozon: OzonClient, ch: ClickHouseClient) -> None:
    logger.info("Starting full products sync: step 1 — fetching product IDs")

    product_ids: list[int] = []
    async for page in await ozon.get_products_list():
        for item in page:
            pid = item.get("product_id")
            if pid:
                product_ids.append(int(pid))
        logger.debug("Collected %d product IDs so far", len(product_ids))

    if not product_ids:
        logger.info("No products found, skipping sync")
        return

    logger.info("Step 2 — fetching product details for %d products", len(product_ids))

    all_details = await ozon.get_products_info(product_ids)
    logger.info("Received details for %d products", len(all_details))

    rows = [_map_product(p) for p in all_details]

    ch.insert_rows("products", _PRODUCTS_COLUMNS, rows)
    ch.optimize_table("products")

    now = datetime.now(timezone.utc)
    ch.save_checkpoint(_SYNC_KEY, _ENTITY_TYPE, now, len(rows))

    logger.info("Products sync complete: %d rows inserted", len(rows))
