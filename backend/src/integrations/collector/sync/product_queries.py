from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_PRODUCT_QUERIES_COLUMNS = [
    "sku",
    "offer_id",
    "name",
    "category",
    "unique_search_users",
    "gmv",
    "date_from",
    "date_to",
    "synced_at",
]

_SKU_BATCH_SIZE = 1000
_PAGE_SIZE = 1000


def _parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _get_week_start(reference: datetime) -> date:
    """Return the Monday of the week containing reference datetime."""
    d = reference.date()
    return d - timedelta(days=d.weekday())


def _map_query_row(
    item: dict[str, Any],
    period_date_from: date,
    period_date_to: date,
    synced_at: datetime,
) -> tuple[Any, ...]:
    return (
        int(item.get("sku", 0) or 0),
        str(item.get("offer_id", "") or ""),
        str(item.get("name", "") or ""),
        str(item.get("category", "") or ""),
        int(item.get("unique_search_users", 0) or 0),
        _parse_decimal(item.get("gmv", 0)),
        period_date_from,
        period_date_to,
        synced_at,
    )


def _get_skus_from_ch(ch: ClickHouseClient) -> list[str]:
    """Query distinct SKUs from stocks table."""
    result = ch.client.query(
        "SELECT DISTINCT toString(sku) FROM stocks WHERE sku > 0"
    )
    return [row[0] for row in result.result_rows if row[0]]


async def sync_product_queries(
    ozon: OzonClient,
    ch: ClickHouseClient,
) -> None:
    now = datetime.now(timezone.utc)
    week_start = _get_week_start(now)
    date_from_str = week_start.strftime("%Y-%m-%dT00:00:00Z")

    logger.info(
        "Starting product queries sync for week starting %s",
        week_start.isoformat(),
    )

    skus = _get_skus_from_ch(ch)
    if not skus:
        logger.info("No SKUs found in stocks table, skipping product queries sync")
        return

    logger.info("Found %d SKUs to query", len(skus))

    synced_at = now
    rows: list[tuple[Any, ...]] = []

    for batch_start in range(0, len(skus), _SKU_BATCH_SIZE):
        batch = skus[batch_start : batch_start + _SKU_BATCH_SIZE]

        period_date_from: date | None = None
        period_date_to: date | None = None

        async for page in ozon.get_product_queries(
            skus=batch,
            date_from=date_from_str,
            page_size=_PAGE_SIZE,
        ):
            # Extract period dates from first page (same for all pages in a batch)
            if period_date_from is None:
                # We'll get it from the first item's batch response — but
                # get_product_queries only yields items, not the full response.
                # Use week_start as fallback; overridden when we have the data.
                period_date_from = week_start
                period_date_to = week_start + timedelta(days=6)

            for item in page:
                row = _map_query_row(
                    item, period_date_from, period_date_to, synced_at
                )
                rows.append(row)

        logger.debug(
            "Batch %d-%d: collected %d rows total",
            batch_start,
            batch_start + len(batch),
            len(rows),
        )

    if not rows:
        logger.info("No product query rows returned, skipping insert")
        return

    ch.insert_rows("product_queries", _PRODUCT_QUERIES_COLUMNS, rows)
    logger.info("Product queries sync complete: %d rows inserted", len(rows))
