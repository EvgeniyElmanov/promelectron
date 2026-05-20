from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_ANALYTICS_COLUMNS = [
    "sku",
    "sku_name",
    "date",
    "revenue",
    "ordered_units",
    "synced_at",
]

# Without Ozon Premium: data only available for the last 3 months
_LOOKBACK_DAYS = 90
_METRICS = ["revenue", "ordered_units"]
_DIMENSION = ["sku", "day"]


def _parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _map_analytics_row(
    item: dict[str, Any],
    synced_at: datetime,
) -> tuple[Any, ...] | None:
    dimensions: list[dict[str, Any]] = item.get("dimensions", [])
    metrics: list[Any] = item.get("metrics", [])

    if len(dimensions) < 2 or len(metrics) < 2:
        return None

    sku_dim = dimensions[0]
    date_dim = dimensions[1]

    try:
        sku = int(sku_dim.get("id", 0) or 0)
    except (ValueError, TypeError):
        return None

    sku_name = str(sku_dim.get("name", "") or "")

    date_str = str(date_dim.get("id", "") or "")
    try:
        row_date = date.fromisoformat(date_str)
    except ValueError:
        return None

    revenue = _parse_decimal(metrics[0])
    ordered_units = int(metrics[1]) if metrics[1] is not None else 0

    return (
        sku,
        sku_name,
        row_date,
        revenue,
        ordered_units,
        synced_at,
    )


async def sync_analytics(
    ozon: OzonClient,
    ch: ClickHouseClient,
    *,
    since: str | None = None,
    full: bool = False,
) -> None:
    now = datetime.now(timezone.utc)

    if since:
        date_from = datetime.fromisoformat(since).date()
    elif full:
        date_from = (now - timedelta(days=_LOOKBACK_DAYS)).date()
    else:
        date_from = (now - timedelta(days=_LOOKBACK_DAYS)).date()

    date_to = now.date()

    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")

    logger.info(
        "Starting analytics sync: %s to %s",
        date_from_str,
        date_to_str,
    )

    synced_at = now
    total_rows = 0
    page_num = 0

    async for page in ozon.get_analytics_data(
        date_from=date_from_str,
        date_to=date_to_str,
        metrics=_METRICS,
        dimension=_DIMENSION,
    ):
        rows: list[tuple[Any, ...]] = []
        for item in page:
            row = _map_analytics_row(item, synced_at)
            if row is not None:
                rows.append(row)
        if rows:
            ch.insert_rows("analytics_sales", _ANALYTICS_COLUMNS, rows)
            total_rows += len(rows)
        page_num += 1
        logger.info("Analytics page %d: %d rows inserted (total: %d)", page_num, len(rows), total_rows)

    logger.info("Analytics sync complete: %d total rows inserted", total_rows)
