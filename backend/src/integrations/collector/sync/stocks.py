from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_STOCKS_COLUMNS = [
    "sku",
    "item_code",
    "item_name",
    "warehouse_name",
    "free_to_sell_amount",
    "promised_amount",
    "reserved_amount",
    "snapshot_at",
]


def _map_stock_row(
    raw: dict[str, Any], snapshot_at: datetime
) -> tuple[Any, ...]:
    return (
        int(raw.get("sku", 0) or 0),
        str(raw.get("item_code", "") or ""),
        str(raw.get("item_name", "") or ""),
        str(raw.get("warehouse_name", "") or ""),
        int(raw.get("free_to_sell_amount", 0) or 0),
        int(raw.get("promised_amount", 0) or 0),
        int(raw.get("reserved_amount", 0) or 0),
        snapshot_at,
    )


async def sync_stocks(ozon: OzonClient, ch: ClickHouseClient) -> None:
    snapshot_at = datetime.now(timezone.utc)
    logger.info("Starting stocks snapshot at %s", snapshot_at.strftime("%Y-%m-%dT%H:%M:%SZ"))

    rows: list[tuple[Any, ...]] = []
    async for page in ozon.get_stock_on_warehouses():
        for item in page:
            rows.append(_map_stock_row(item, snapshot_at))
        logger.debug("Collected %d stock rows so far", len(rows))

    if not rows:
        logger.info("No stock rows returned, skipping insert")
        return

    ch.insert_rows("stocks", _STOCKS_COLUMNS, rows)
    logger.info("Stocks snapshot complete: %d rows inserted", len(rows))
