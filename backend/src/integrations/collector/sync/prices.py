from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_PRICES_COLUMNS = [
    "product_id",
    "offer_id",
    "currency_code",
    "price",
    "marketing_seller_price",
    "min_price",
    "old_price",
    "retail_price",
    "net_price",
    "vat",
    "auto_action_enabled",
    "acquiring",
    "volume_weight",
    "sales_percent_fbo",
    "sales_percent_fbs",
    "price_index_color",
    "ozon_index_min_price",
    "ozon_index_value",
    "external_index_min_price",
    "external_index_value",
    "self_marketplaces_index_min_price",
    "self_marketplaces_index_value",
    "updated_at",
]

_SYNC_KEY = "global"
_ENTITY_TYPE = "prices"


def _parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _map_price_row(
    raw: dict[str, Any], synced_at: datetime
) -> tuple[Any, ...]:
    price_block: dict[str, Any] = raw.get("price", {}) or {}
    indexes: dict[str, Any] = raw.get("price_indexes", {}) or {}
    commissions: dict[str, Any] = raw.get("commissions", {}) or {}

    ozon_idx: dict[str, Any] = indexes.get("ozon_index_data", {}) or {}
    ext_idx: dict[str, Any] = indexes.get("external_index_data", {}) or {}
    self_idx: dict[str, Any] = indexes.get("self_marketplaces_index_data", {}) or {}

    return (
        int(raw.get("product_id", 0) or 0),
        str(raw.get("offer_id", "") or ""),
        str(price_block.get("currency_code", "") or ""),
        _parse_decimal(price_block.get("price", 0)),
        _parse_decimal(price_block.get("marketing_seller_price", 0)),
        _parse_decimal(price_block.get("min_price", 0)),
        _parse_decimal(price_block.get("old_price", 0)),
        _parse_decimal(price_block.get("retail_price", 0)),
        _parse_decimal(price_block.get("net_price", 0)),
        float(price_block.get("vat", 0) or 0),
        int(bool(price_block.get("auto_action_enabled", False))),
        float(raw.get("acquiring", 0) or 0),
        float(raw.get("volume_weight", 0) or 0),
        float(commissions.get("sales_percent_fbo", 0) or 0),
        float(commissions.get("sales_percent_fbs", 0) or 0),
        str(indexes.get("color_index", "") or ""),
        _parse_decimal(ozon_idx.get("min_price", 0)),
        float(ozon_idx.get("price_index_value", 0) or 0),
        _parse_decimal(ext_idx.get("min_price", 0)),
        float(ext_idx.get("price_index_value", 0) or 0),
        _parse_decimal(self_idx.get("min_price", 0)),
        float(self_idx.get("price_index_value", 0) or 0),
        synced_at,
    )


async def sync_prices(ozon: OzonClient, ch: ClickHouseClient) -> None:
    synced_at = datetime.now(timezone.utc)
    logger.info("Starting prices sync at %s", synced_at.strftime("%Y-%m-%dT%H:%M:%SZ"))

    rows: list[tuple[Any, ...]] = []
    async for page in await ozon.get_prices():
        for item in page:
            rows.append(_map_price_row(item, synced_at))
        logger.debug("Collected %d price rows so far", len(rows))

    if not rows:
        logger.info("No price rows returned, skipping insert")
        return

    ch.insert_rows("prices", _PRICES_COLUMNS, rows)
    ch.optimize_table("prices")

    ch.save_checkpoint(_SYNC_KEY, _ENTITY_TYPE, synced_at, len(rows))
    logger.info("Prices sync complete: %d rows inserted", len(rows))
