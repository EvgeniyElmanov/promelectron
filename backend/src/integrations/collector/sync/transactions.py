from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_TRANSACTIONS_COLUMNS = [
    "operation_id",
    "operation_type",
    "operation_type_name",
    "operation_date",
    "posting_number",
    "delivery_schema",
    "amount",
    "accruals_for_sale",
    "sale_commission",
    "delivery_charge",
    "return_delivery_charge",
    "item_sku",
    "item_name",
    "service_names",
    "service_prices",
]

_SYNC_KEY = "global"
_ENTITY_TYPE = "transactions"
_DEFAULT_LOOKBACK_DAYS = 30
# Ozon API max period per request is 1 month (31 days to be safe)
_MAX_CHUNK_DAYS = 28


def _parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _parse_operation_date(value: Any) -> datetime:
    """Parse operation_date which comes as 'YYYY-MM-DD HH:MM:SS' (no Z, UTC)."""
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    try:
        text = str(value).strip().rstrip("Z")
        dt = datetime.fromisoformat(text)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _map_operation(op: dict[str, Any]) -> tuple[Any, ...]:
    operation_id = int(op.get("operation_id", 0) or 0)
    operation_type = str(op.get("operation_type", "") or "")
    operation_type_name = str(op.get("operation_type_name", "") or "")
    operation_date = _parse_operation_date(op.get("operation_date"))

    posting: dict[str, Any] = op.get("posting") or {}
    posting_number = str(posting.get("posting_number", "") or "")
    delivery_schema = str(posting.get("delivery_schema", "") or "")

    amount = _parse_decimal(op.get("amount", "0"))
    accruals_for_sale = _parse_decimal(op.get("accruals_for_sale", "0"))
    sale_commission = _parse_decimal(op.get("sale_commission", "0"))
    delivery_charge = _parse_decimal(op.get("delivery_charge", "0"))
    return_delivery_charge = _parse_decimal(op.get("return_delivery_charge", "0"))

    items: list[dict[str, Any]] = op.get("items") or []
    first_item = items[0] if items else {}
    item_sku = int(first_item.get("sku", 0) or 0)
    item_name = str(first_item.get("name", "") or "")

    services: list[dict[str, Any]] = op.get("services") or []
    service_names = [str(s.get("name", "") or "") for s in services]
    service_prices = [_parse_decimal(s.get("price", "0")) for s in services]

    return (
        operation_id,
        operation_type,
        operation_type_name,
        operation_date,
        posting_number,
        delivery_schema,
        amount,
        accruals_for_sale,
        sale_commission,
        delivery_charge,
        return_delivery_charge,
        item_sku,
        item_name,
        service_names,
        service_prices,
    )


def _month_chunks(
    start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into chunks of at most _MAX_CHUNK_DAYS days."""
    chunks: list[tuple[datetime, datetime]] = []
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=_MAX_CHUNK_DAYS), end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(seconds=1)
    return chunks


async def sync_transactions(
    ozon: OzonClient,
    ch: ClickHouseClient,
    *,
    since: str | None = None,
    full: bool = False,
) -> None:
    now = datetime.now(timezone.utc)

    if since:
        since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    elif full:
        # Full sync: get all historical transactions
        since_dt = now - timedelta(days=365 * 3)
    else:
        checkpoint = ch.get_checkpoint(_SYNC_KEY, _ENTITY_TYPE)
        if checkpoint:
            since_dt = checkpoint - timedelta(days=1)
        else:
            since_dt = now - timedelta(days=365 * 3)

    chunks = _month_chunks(since_dt, now)
    logger.info(
        "Syncing transactions from %s to %s (%d chunk(s))",
        since_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        len(chunks),
    )

    all_rows: list[tuple[Any, ...]] = []

    for chunk_start, chunk_end in chunks:
        from_str = chunk_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        to_str = chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.debug("Fetching transactions chunk %s .. %s", from_str, to_str)

        chunk_count = 0
        async for page in await ozon.get_transactions(from_str, to_str):
            for op in page:
                all_rows.append(_map_operation(op))
            chunk_count += len(page)

        logger.info(
            "Chunk %s .. %s: %d operations", from_str, to_str, chunk_count
        )

    if not all_rows:
        logger.info("No transaction rows to insert")
        ch.save_checkpoint(_SYNC_KEY, _ENTITY_TYPE, now, 0)
        return

    ch.insert_rows("transactions", _TRANSACTIONS_COLUMNS, all_rows)

    ch.save_checkpoint(_SYNC_KEY, _ENTITY_TYPE, now, len(all_rows))
    logger.info("Transactions sync complete: %d rows inserted", len(all_rows))
