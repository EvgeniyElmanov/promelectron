import logging
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from itertools import batched
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.category import Category
from src.app.models.job import Job
from src.app.models.onec_sync import OnecChangeLog
from src.app.models.product import Product
from src.app.schemas.onec import (
    OnecCategoryOdata,
    OnecChange,
    OnecPriceOdata,
    OnecProductOdata,
    OnecStockOdata,
    OnecWebhookPayload,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


async def _resolve_category_by_id(session: AsyncSession, category_id: str | int | None) -> int | None:
    """Resolve a category identifier to the internal Category.id.

    If the value is a string we treat it as a 1C external id (onec_id).
    If it is already an int we return it as-is.
    """
    if category_id is None:
        return None
    if isinstance(category_id, int):
        return category_id
    result = await session.execute(
        select(Category).where(Category.onec_id == str(category_id))
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise ValueError(f"Category with onec_id={category_id!r} not found")
    return category.id


async def _resolve_category_parent_id(session: AsyncSession, parent_onec_id: str | int | None) -> int | None:
    """Resolve a parent identifier to the internal Category.id.

    If the value is a string we treat it as a 1C external id (onec_id).
    If it is already an int we return it as-is.
    """
    if parent_onec_id is None:
        return None
    if isinstance(parent_onec_id, int):
        return parent_onec_id
    result = await session.execute(
        select(Category).where(Category.onec_id == str(parent_onec_id))
    )
    parent = result.scalar_one_or_none()
    return parent.id if parent else None


def _is_stale_change(change_version: datetime, existing_sync_at: datetime | None) -> bool:
    """Return True if the incoming change is older or equal to the existing entity."""
    if existing_sync_at is None:
        return False
    return change_version <= existing_sync_at


async def apply_product_change(session: AsyncSession, change: OnecChange) -> Product | None:
    """Apply a single 1C product change: create, update or soft-delete."""
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()

    data = change.data
    is_new_product = product is None
    if is_new_product:
        if "supplier_id" not in data:
            raise ValueError("supplier_id is required for product creation")
        product = Product(onec_id=change.external_id)
        session.add(product)

    if _is_stale_change(change.version, product.onec_sync_at):
        return product

    # Set required fields first so any autoflush triggered by FK resolution
    # (e.g. category_id lookup) sees a valid product row.
    if "name" in data:
        product.name = data["name"]
    if "description" in data:
        product.description = data["description"]
    if "sku" in data:
        product.sku = data["sku"]
    if "price" in data:
        product.price = data["price"]
    if "stock" in data:
        product.stock = data["stock"]
    if "supplier_id" in data:
        product.supplier_id = data["supplier_id"]
    if "is_active" in data:
        product.is_active = data["is_active"]

    # Resolve foreign keys after all required fields are present.
    if "category_id" in data:
        product.category_id = await _resolve_category_by_id(session, data["category_id"])

    if change.action == "delete":
        product.is_active = False

    product.onec_sync_at = change.version
    return product


async def apply_category_change(session: AsyncSession, change: OnecChange) -> Category | None:
    """Apply a single 1C category change: create, update or soft-delete."""
    result = await session.execute(
        select(Category).where(Category.onec_id == change.external_id)
    )
    category = result.scalar_one_or_none()

    data = change.data
    if category is None:
        category = Category(onec_id=change.external_id)
        session.add(category)

    if _is_stale_change(change.version, category.onec_sync_at):
        return category

    if "name" in data:
        category.name = data["name"]
    if "description" in data:
        category.description = data["description"]
    if "parent_id" in data:
        category.parent_id = await _resolve_category_parent_id(session, data["parent_id"])
    if "is_active" in data:
        category.is_active = data["is_active"]

    if change.action == "delete":
        category.is_active = False

    category.onec_sync_at = change.version
    return category


async def apply_price_change(session: AsyncSession, change: OnecChange) -> Product | None:
    """Apply a 1C price change to an existing product.

    If the product does not exist yet (e.g. product batch has not been applied)
    the change is silently skipped so the queue stays idempotent.
    """
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    if _is_stale_change(change.version, product.onec_sync_at):
        return product

    if "price" in change.data:
        product.price = change.data["price"]

    product.onec_sync_at = change.version
    return product


async def apply_stock_change(session: AsyncSession, change: OnecChange) -> Product | None:
    """Apply a 1C stock balance change to an existing product.

    If the product does not exist yet (e.g. product batch has not been applied)
    the change is silently skipped so the queue stays idempotent.
    """
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    if _is_stale_change(change.version, product.onec_sync_at):
        return product

    if "stock" in change.data:
        product.stock = change.data["stock"]

    product.onec_sync_at = change.version
    return product


async def handle_onec_apply_changes(session: AsyncSession, payload: dict) -> None:
    """Process an ONEC_APPLY_CHANGES job payload and update the catalog."""
    log_id = payload.get("log_id")
    if not log_id:
        raise ValueError("ONEC_APPLY_CHANGES job missing log_id")

    result = await session.execute(
        select(OnecChangeLog).where(OnecChangeLog.id == log_id).with_for_update()
    )
    log = result.scalar_one_or_none()
    if not log:
        raise ValueError(f"OnecChangeLog {log_id} not found")

    log.status = "processing"
    log.processed_at = datetime.now(timezone.utc)
    await session.flush()

    try:
        webhook_payload = OnecWebhookPayload.model_validate(log.payload)
        handler = {
            "product": apply_product_change,
            "category": apply_category_change,
            "price": apply_price_change,
            "stock": apply_stock_change,
            "order_status": apply_order_status_change,
        }.get(webhook_payload.entity_type)

        if not handler:
            raise ValueError(f"Unsupported entity_type: {webhook_payload.entity_type}")

        async with session.begin_nested():
            for change in webhook_payload.changes:
                await handler(session, change)

        log.status = "done"
        log.applied_at = datetime.now(timezone.utc)
        log.error_message = None
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        log.retry_count += 1
        raise


async def apply_order_status_change(session: AsyncSession, change: OnecChange) -> None:
    """Placeholder for order status changes from 1C.

    order_status handling is out of scope for Phase 1; log and skip silently
    so the queue stays idempotent and does not fail the whole batch.
    """
    logger.warning("order_status changes are not implemented yet: %s", change.external_id)


# ─── Mapping helpers for pull fallback (OData → OnecChange) ──────────────────


def build_category_change(category: OnecCategoryOdata, version: datetime) -> OnecChange:
    return OnecChange(
        external_id=category.ref_key,
        action="update",
        version=version,
        data={
            "name": category.description,
            "parent_id": category.parent_key,
            "is_active": True,
        },
    )


def build_product_change(product: OnecProductOdata, version: datetime, supplier_id: int | None) -> OnecChange:
    return OnecChange(
        external_id=product.ref_key,
        action="update",
        version=version,
        data={
            "name": product.description,
            "sku": product.article or product.code,
            "category_id": product.parent_key,
            "supplier_id": supplier_id,
            "is_active": True,
        },
    )


def build_price_change(price: OnecPriceOdata, version: datetime) -> OnecChange:
    return OnecChange(
        external_id=price.product_key,
        action="update",
        version=version,
        data={"price": price.price},
    )


def build_stock_change(stock: OnecStockOdata, version: datetime) -> OnecChange:
    return OnecChange(
        external_id=stock.product_key,
        action="update",
        version=version,
        data={"stock": int(stock.quantity)},
    )


def build_onec_webhook_payload(
    entity_type: str,
    changes: list[OnecChange],
    batch_id: UUID,
    sent_at: datetime,
    base_name: str,
) -> OnecWebhookPayload:
    return OnecWebhookPayload(
        batch_id=batch_id,
        sent_at=sent_at,
        base_name=base_name,
        entity_type=entity_type,  # type: ignore[arg-type]
        changes=changes,
    )


def _pull_batch_checksum(entity_type: str, changes: list[OnecChange], version: datetime) -> str:
    """Deterministic checksum for a pull fallback batch to avoid duplicates."""
    payload = "|".join(
        [entity_type, version.isoformat()]
        + sorted(change.external_id for change in changes)
    )
    return sha256(payload.encode()).hexdigest()


async def _enqueue_change_log_batch(
    session: AsyncSession,
    entity_type: str,
    changes: list[OnecChange],
    sent_at: datetime,
    base_name: str,
) -> None:
    """Persist one OnecChangeLog + ONEC_APPLY_CHANGES job for a batch of changes."""
    if not changes:
        return
    payload = build_onec_webhook_payload(
        entity_type=entity_type,
        changes=changes,
        batch_id=uuid4(),
        sent_at=sent_at,
        base_name=base_name,
    )
    log = OnecChangeLog(
        batch_id=payload.batch_id,
        entity_type=entity_type,
        source=base_name,
        payload=payload.model_dump(mode="json"),
        status="pending",
        checksum=_pull_batch_checksum(entity_type, changes, sent_at),
    )
    session.add(log)
    await session.flush()
    await session.refresh(log)
    session.add(Job(job_type="ONEC_APPLY_CHANGES", payload={"log_id": log.id}))


async def create_onec_full_sync_job(session: AsyncSession) -> Job:
    """Create an ONEC_FULL_SYNC job for later processing by the worker."""
    job = Job(job_type="ONEC_FULL_SYNC", payload={})
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job


async def run_onec_full_sync(
    session: AsyncSession,
    default_supplier_id: int | None = None,
) -> None:
    """Pull catalog data from 1C and enqueue ONEC_APPLY_CHANGES jobs.

    This helper is invoked by ``handle_onec_full_sync`` in the job worker.
    It does **not** apply changes synchronously — it only enqueues batches.
    """
    from src.app.workers.onec_client import OnecClient

    supplier_id = default_supplier_id or settings.onec_default_supplier_id

    async with OnecClient() as client:
        if not client.base_url:
            raise ValueError("ONEC_API_URL is not configured")

        base_sent_at = datetime.now(timezone.utc)
        base_name = "1c-unf-full-sync"

        # Use monotonically increasing versions per entity type so that
        # price/stock batches are not rejected as stale after product batches.
        def _version(offset_ms: int) -> datetime:
            return base_sent_at + timedelta(milliseconds=offset_ms)

        categories = await client.get_all_categories()
        for chunk in batched(categories, BATCH_SIZE):
            changes = [build_category_change(c, _version(0)) for c in chunk]
            await _enqueue_change_log_batch(session, "category", changes, _version(0), base_name)

        products = await client.get_all_products()
        for chunk in batched(products, BATCH_SIZE):
            changes = [build_product_change(p, _version(100), supplier_id) for p in chunk]
            await _enqueue_change_log_batch(session, "product", changes, _version(100), base_name)

        prices = await client.get_all_prices()
        for chunk in batched(prices, BATCH_SIZE):
            changes = [build_price_change(p, _version(200)) for p in chunk]
            await _enqueue_change_log_batch(session, "price", changes, _version(200), base_name)

        stocks = await client.get_all_stock_balance()
        for chunk in batched(stocks, BATCH_SIZE):
            changes = [build_stock_change(s, _version(300)) for s in chunk]
            await _enqueue_change_log_batch(session, "stock", changes, _version(300), base_name)
