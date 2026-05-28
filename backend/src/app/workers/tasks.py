import logging
import time
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import SessionLocal
from src.app.models.category import Category
from src.app.models.product import Product
from src.app.models.supplier import Supplier
from src.app.workers.onec_client import OnecClient

logger = logging.getLogger(__name__)

SEED_SUPPLIER_API_KEY = "seed-supplier-api-key"


async def _get_or_create_category(session: AsyncSession, name: str | None) -> Category | None:
    if not name:
        return None
    result = await session.execute(select(Category).where(Category.name == name))
    category = result.scalar_one_or_none()
    if category:
        return category
    category = Category(name=name, created_at=datetime.now(timezone.utc))
    session.add(category)
    await session.flush()
    logger.info("Created category: %s", name)
    return category


async def _ensure_import_supplier(session: AsyncSession) -> Supplier | None:
    result = await session.execute(
        select(Supplier).where(Supplier.api_key == SEED_SUPPLIER_API_KEY)
    )
    supplier = result.scalar_one_or_none()
    if supplier:
        return supplier
    # No seed supplier — cannot assign products
    logger.warning("Seed supplier not found — product sync will be skipped")
    return None


async def _sync_products_task(session: AsyncSession | None = None) -> dict:
    client = OnecClient()
    onec_products = client.get_products()

    if not onec_products:
        logger.info("No products returned from 1C — nothing to sync")
        return {"created": 0, "updated": 0, "deactivated": 0, "errors": 0, "duration_ms": 0}

    start = time.time()
    created = updated = deactivated = errors = 0
    processed_skus: set[str] = set()

    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        supplier = await _ensure_import_supplier(session)
        if not supplier:
            return {
                "created": 0,
                "updated": 0,
                "deactivated": 0,
                "errors": len(onec_products),
                "duration_ms": int((time.time() - start) * 1000),
            }

        for op in onec_products:
            if not op.sku:
                logger.warning("Skipping 1C product without SKU: %s", op.name)
                errors += 1
                continue

            processed_skus.add(op.sku)

            try:
                result = await session.execute(
                    select(Product).where(Product.sku == op.sku)
                )
                product = result.scalar_one_or_none()

                category = await _get_or_create_category(session, op.category_name)

                if product is None:
                    product = Product(
                        sku=op.sku,
                        name=op.name,
                        description=op.description or "",
                        price=op.price,
                        stock=op.stock,
                        is_active=op.is_active,
                        category_id=category.id if category else None,
                        supplier_id=supplier.id,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(product)
                    created += 1
                    logger.info("Created product %s — %s", op.sku, op.name)
                else:
                    product.name = op.name
                    product.description = op.description or ""
                    product.price = op.price
                    product.stock = op.stock
                    product.is_active = op.is_active
                    product.category_id = category.id if category else product.category_id
                    product.updated_at = datetime.now(timezone.utc)
                    updated += 1
                    logger.info("Updated product %s — %s", op.sku, op.name)

                await session.flush()
            except Exception as exc:
                logger.exception("Failed to sync product %s: %s", op.sku, exc)
                errors += 1
                continue

        # Deactivate products not present in 1C feed
        try:
            missing_result = await session.execute(
                select(Product).where(
                    Product.sku.isnot(None),
                    Product.sku.not_in(list(processed_skus)),
                    Product.is_active.is_(True),
                )
            )
            for product in missing_result.scalars().all():
                product.is_active = False
                product.updated_at = datetime.now(timezone.utc)
                deactivated += 1
                logger.info("Deactivated missing product %s", product.sku)
            await session.flush()
        except Exception:
            logger.exception("Failed to deactivate missing products")

        await session.commit()
    finally:
        if close_session:
            await session.close()

    duration_ms = int((time.time() - start) * 1000)
    logger.info(
        "1C sync completed in %sms — created=%s updated=%s deactivated=%s errors=%s",
        duration_ms,
        created,
        updated,
        deactivated,
        errors,
    )
    return {
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "errors": errors,
        "duration_ms": duration_ms,
    }


@shared_task(bind=True, name="src.app.workers.tasks.sync_products_from_onec")
def sync_products_from_onec(self) -> dict:
    """Celery task: synchronize products from 1C ERP."""
    import asyncio

    logger.info("Starting 1C product sync task [task_id=%s]", self.request.id)
    return asyncio.run(_sync_products_task())
