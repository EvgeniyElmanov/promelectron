import asyncio
import logging

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.db.database import SessionLocal
from src.app.models.order import Order
from src.app.services.cdek_client import CdekAPIError
from src.app.services.cdek_service import CdekService

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


async def _create_cdek_order_task(order_id: int) -> dict:
    session: AsyncSession = SessionLocal()
    try:
        result = await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.user))
        )
        order = result.scalars().first()
        if not order:
            logger.warning("Order %s not found for CDEK sync", order_id)
            return {"success": False, "error": "Order not found"}

        if order.cdek_uuid:
            logger.info("Order %s already has CDEK uuid %s", order_id, order.cdek_uuid)
            return {"success": True, "cdek_uuid": order.cdek_uuid}

        try:
            cdek_result = await CdekService.create_cdek_order(order, session)
        except CdekAPIError as exc:
            logger.exception("CDEK API error for order %s: %s", order_id, exc)
            order.cdek_sync_attempts += 1
            order.cdek_sync_failed = True
            await session.commit()
            return {"success": False, "error": str(exc)}

        entity = cdek_result.get("entity", {})
        cdek_uuid = entity.get("uuid")
        if cdek_uuid:
            order.cdek_uuid = cdek_uuid
            order.cdek_sync_failed = False
            await session.commit()
            logger.info("CDEK order created for order %s: uuid=%s", order_id, cdek_uuid)
            return {"success": True, "cdek_uuid": cdek_uuid}

        # Accepted but no uuid yet (should not happen, but handle gracefully)
        order.cdek_sync_attempts += 1
        order.cdek_sync_failed = True
        await session.commit()
        logger.warning("CDEK create order for %s returned no uuid: %s", order_id, cdek_result)
        return {"success": False, "error": "No uuid in CDEK response"}
    finally:
        await session.close()


@shared_task(bind=True, name="src.app.workers.cdek_tasks.create_cdek_order_task", max_retries=MAX_RETRIES)
def create_cdek_order_task(self, order_id: int) -> dict:
    """Celery task: create order in CDEK with retries."""
    logger.info("Starting CDEK order creation task [order_id=%s, attempt=%s]", order_id, self.request.retries)
    result = asyncio.run(_create_cdek_order_task(order_id))

    if not result.get("success") and self.request.retries < MAX_RETRIES:
        countdown = 60 * (2 ** self.request.retries)
        logger.warning("Retrying CDEK order creation for order %s in %ss", order_id, countdown)
        raise self.retry(countdown=countdown, exc=Exception(result.get("error", "Unknown error")))

    return result


async def _sync_cdek_order_statuses() -> dict:
    """Poll CDEK for order statuses as a webhook fallback."""
    session: AsyncSession = SessionLocal()
    try:
        return await CdekService.sync_order_statuses(session)
    finally:
        await session.close()


@shared_task(name="src.app.workers.cdek_tasks.sync_cdek_order_statuses")
def sync_cdek_order_statuses() -> dict:
    """Celery periodic task: sync CDEK order statuses."""
    logger.info("Starting CDEK order status sync")
    return asyncio.run(_sync_cdek_order_statuses())
