import asyncio
import logging
import os
import signal
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.core.config import settings
from src.app.db.database import SessionLocal
from src.app.models.cdek_order import CdekOrder
from src.app.models.job import Job
from src.app.models.order import Order
from src.app.services.cdek_client import CdekAPIError, CdekClient
from src.app.services.cdek_service import CdekService
from src.app.services.email_service import EmailService
from src.app.services.onec_intake_loader import process_intake
from src.app.services.onec_sync_service import handle_onec_apply_changes, run_onec_full_sync

logger = logging.getLogger(__name__)

SHUTDOWN_EVENT = asyncio.Event()


async def _ensure_sync_job(cdek_order_id: int, db: AsyncSession) -> None:
    """Create a follow-up CDEK_SYNC_ORDER_STATUS job if one does not exist."""
    existing = await db.execute(
        select(Job)
        .where(
            Job.job_type == "CDEK_SYNC_ORDER_STATUS",
            Job.payload.contains({"cdek_order_id": cdek_order_id}),
            Job.status.in_(["pending", "running"]),
        )
    )
    if existing.scalars().first():
        return
    db.add(Job(job_type="CDEK_SYNC_ORDER_STATUS", payload={"cdek_order_id": cdek_order_id}))


async def handle_cdek_create_order(job: Job, db: AsyncSession) -> None:
    """Create CDEK order via API and schedule status sync job on success."""
    order_id = job.payload.get("order_id")
    if not order_id:
        raise ValueError("CDEK_CREATE_ORDER job missing order_id")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items),
            selectinload(Order.cdek_order),
            selectinload(Order.recipient),
        )
    )
    order = result.scalars().first()
    if not order:
        raise ValueError(f"Order {order_id} not found")

    job.status = "running"
    cdek_order = await CdekService.create_cdek_order(order, db)
    if not cdek_order or not cdek_order.cdek_uuid:
        raise ValueError(f"CDEK order creation failed for order {order_id}: no cdek_uuid returned")
    await _ensure_sync_job(cdek_order.id, db)
    await db.commit()


async def handle_cdek_sync_status(job: Job, db: AsyncSession) -> None:
    """Poll CDEK for a single order status and reschedule until terminal."""
    job.status = "running"
    cdek_order_id = job.payload.get("cdek_order_id")
    if not cdek_order_id:
        raise ValueError("CDEK_SYNC_ORDER_STATUS job missing cdek_order_id")

    result = await db.execute(
        select(CdekOrder)
        .where(CdekOrder.id == cdek_order_id)
        .options(selectinload(CdekOrder.order))
    )
    cdek_order = result.scalars().first()
    if not cdek_order:
        raise ValueError(f"CdekOrder {cdek_order_id} not found")

    if not cdek_order.cdek_uuid:
        raise ValueError(f"CdekOrder {cdek_order_id} has no CDEK uuid")

    client = CdekClient()
    try:
        data = await client.get_order(cdek_order.cdek_uuid)
    finally:
        await client.close()

    await CdekService.apply_cdek_status(cdek_order, data, db, source="polling")

    # Reschedule unless we hit a terminal status
    if cdek_order.cdek_status not in settings.cdek_terminal_statuses:
        job.run_after = datetime.now(timezone.utc) + timedelta(
            seconds=settings.cdek_sync_cron_interval_seconds
        )
        job.status = "pending"


async def handle_send_email(job: Job, db: AsyncSession) -> None:
    """Send an email using the payload prepared at enqueue time.

    Records the delivery outcome in ``job.processing_log`` so a ``completed``
    job can still be distinguished from a silent fallback/failure.
    """
    payload = job.payload
    result = await EmailService.send_email(
        to=payload["to"],
        subject=payload["subject"],
        html_body=payload["html"],
        text_body=payload.get("text", ""),
    )
    job.processing_log.append(f"send_email: {result}")


async def handle_onec_apply_changes_job(job: Job, db: AsyncSession) -> None:
    """Apply 1C catalog changes captured by the webhook."""
    await handle_onec_apply_changes(db, job.payload)


async def handle_onec_full_sync_job(job: Job, db: AsyncSession) -> None:
    """Pull catalog data from 1C and enqueue per-entity apply jobs."""
    await run_onec_full_sync(db, default_supplier_id=settings.onec_default_supplier_id)


async def handle_onec_intake_process_job(job: Job, db: AsyncSession) -> None:
    """Parse a raw 1C intake file from MinIO and upsert it into the catalog.

    The loader enqueues SEARCH_INDEX_PRODUCTS jobs for touched products.
    NB: the SEARCH_INDEX_PRODUCTS handler itself lands in Phase 5 (epic #117);
    until then those jobs fail with "Unknown job_type" — accepted behavior
    (decision for #120, 2026-07-31).
    """
    intake_id = job.payload.get("intake_id")
    if not intake_id:
        raise ValueError("ONEC_INTAKE_PROCESS job missing intake_id")
    stats = await process_intake(db, intake_id)
    job.processing_log.append(f"intake {intake_id}: {stats.summary()}"[:500])


HANDLERS: dict[str, Callable[[Job, AsyncSession], Awaitable[None]]] = {
    "CDEK_CREATE_ORDER": handle_cdek_create_order,
    "CDEK_SYNC_ORDER_STATUS": handle_cdek_sync_status,
    "SEND_EMAIL": handle_send_email,
    "ONEC_APPLY_CHANGES": handle_onec_apply_changes_job,
    "ONEC_FULL_SYNC": handle_onec_full_sync_job,
    "ONEC_INTAKE_PROCESS": handle_onec_intake_process_job,
}


async def reset_stuck_jobs(session_factory: Callable[[], AsyncSession] | None = None) -> int:
    """Reset jobs stuck in 'running' back to pending so they can be retried."""
    if session_factory is None:
        session_factory = SessionLocal
    session: AsyncSession = session_factory()
    try:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Job)
            .where(Job.status == "running", Job.timeout < now)
            .with_for_update(skip_locked=True)
        )
        jobs = result.scalars().all()
        count = 0
        for job in jobs:
            job.attempts += 1
            if job.attempts >= settings.job_max_attempts:
                job.status = "failed"
                job.timeout = None
                logger.warning("Job %s marked failed after stuck timeout", job.id)
            else:
                job.status = "pending"
                job.run_after = now
                job.timeout = None
                logger.info("Reset stuck job %s to pending", job.id)
            count += 1
        await session.commit()
        return count
    finally:
        await session.close()


async def process_jobs(session_factory: "callable | None" = None) -> int:
    """Fetch and process a batch of pending jobs. Returns number processed."""
    if session_factory is None:
        session_factory = SessionLocal
    session: AsyncSession = session_factory()
    processed = 0
    try:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Job)
            .where(
                Job.status == "pending",
                Job.run_after <= now,
                Job.attempts < settings.job_max_attempts,
            )
            .order_by(Job.run_after)
            .limit(100)
            .with_for_update(skip_locked=True)
        )
        jobs = result.scalars().all()

        for job in jobs:
            handler = HANDLERS.get(job.job_type)
            if not handler:
                job.status = "failed"
                job.processing_log.append(f"Unknown job_type: {job.job_type}")
                await session.commit()
                continue

            job.status = "running"
            job.timeout = now + timedelta(seconds=settings.job_worker_sleep_seconds * 2)
            await session.commit()

            try:
                await handler(job, session)
                if job.status == "running":
                    job.status = "completed"
                    job.timeout = None
                processed += 1
            except CdekAPIError as exc:
                job.attempts += 1
                job.status = "pending" if job.attempts < settings.job_max_attempts else "failed"
                job.run_after = now + timedelta(seconds=settings.job_worker_sleep_seconds)
                job.timeout = None
                job.processing_log.append(f"CdekAPIError: {exc}"[:500])
                logger.warning(
                    "Job %s failed (attempt %s): %s",
                    job.id,
                    job.attempts,
                    exc,
                )
            except Exception as exc:
                job.attempts += 1
                job.status = "pending" if job.attempts < settings.job_max_attempts else "failed"
                job.run_after = now + timedelta(seconds=settings.job_worker_sleep_seconds)
                job.timeout = None
                job.processing_log.append(str(exc)[:500])
                logger.exception("Job %s failed", job.id)

            await session.commit()

        return processed
    finally:
        await session.close()


async def run_worker() -> None:
    """Main polling loop with graceful shutdown."""
    logger.info(
        "Job worker started (sleep=%ss, max_attempts=%s)",
        settings.job_worker_sleep_seconds,
        settings.job_max_attempts,
    )
    try:
        stuck_count = await reset_stuck_jobs()
        if stuck_count:
            logger.info("Reset %s stuck jobs on startup", stuck_count)
    except Exception:
        logger.exception("Failed to reset stuck jobs on startup")
    while not SHUTDOWN_EVENT.is_set():
        try:
            processed = await process_jobs()
            if processed:
                logger.info("Processed %s jobs", processed)
        except Exception:
            logger.exception("Job worker loop error")

        try:
            await asyncio.wait_for(
                SHUTDOWN_EVENT.wait(),
                timeout=settings.job_worker_sleep_seconds,
            )
        except asyncio.TimeoutError:
            pass

    logger.info("Job worker shutting down")


def _signal_handler(signum: int) -> None:
    logger.info("Received signal %s, shutting down", signum)
    SHUTDOWN_EVENT.set()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
