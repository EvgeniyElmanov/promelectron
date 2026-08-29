"""Cronjob: create CDEK_SYNC_ORDER_STATUS jobs for non-terminal CDEK orders."""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.db.database import SessionLocal
from src.app.models.cdek_order import CdekOrder
from src.app.models.job import Job

logger = logging.getLogger(__name__)


async def run() -> dict[str, int]:
    session: AsyncSession = SessionLocal()
    created = 0
    try:
        result = await session.execute(
            select(CdekOrder).where(
                CdekOrder.cdek_uuid.isnot(None),
                CdekOrder.sync_failed.is_(False),
                CdekOrder.cdek_status.not_in(list(settings.cdek_terminal_statuses))
                | CdekOrder.cdek_status.is_(None),
            )
        )
        cdek_orders = result.scalars().all()

        for cdek_order in cdek_orders:
            existing = await session.execute(
                select(Job)
                .where(
                    Job.job_type == "CDEK_SYNC_ORDER_STATUS",
                    Job.payload.contains({"cdek_order_id": cdek_order.id}),
                    Job.status.in_(["pending", "running"]),
                )
            )
            if existing.scalars().first():
                continue

            session.add(
                Job(
                    job_type="CDEK_SYNC_ORDER_STATUS",
                    payload={"cdek_order_id": cdek_order.id},
                )
            )
            created += 1

        await session.commit()
        logger.info(
            "Created %s CDEK_SYNC_ORDER_STATUS jobs from %s candidates",
            created,
            len(cdek_orders),
        )
        return {"created": created, "candidates": len(cdek_orders)}
    finally:
        await session.close()


def main() -> None:
    result = asyncio.run(run())
    print(result)


if __name__ == "__main__":
    main()
