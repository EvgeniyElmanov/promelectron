from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.category import Category
from src.app.models.onec_sync import OnecChangeLog
from src.app.models.product import Product
from src.app.schemas.onec import OnecChange, OnecWebhookPayload


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
