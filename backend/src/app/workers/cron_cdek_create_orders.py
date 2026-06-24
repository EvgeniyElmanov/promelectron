"""Cronjob: create CDEK_CREATE_ORDER jobs for paid orders without a CDEK uuid.

This is a safety net in case the payment-success path fails to enqueue the job.
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import SessionLocal
from src.app.models.cdek_order import CdekOrder
from src.app.models.job import Job
from src.app.models.order import Order

logger = logging.getLogger(__name__)


async def run() -> dict[str, int]:
    session: AsyncSession = SessionLocal()
    created = 0
    try:
        result = await session.execute(
            select(Order)
            .join(CdekOrder, Order.cdek_order_id == CdekOrder.id)
            .where(
                Order.status == "paid",
                CdekOrder.cdek_uuid.is_(None),
            )
        )
        orders = result.scalars().all()

        for order in orders:
            existing = await session.execute(
                select(Job)
                .where(
                    Job.job_type == "CDEK_CREATE_ORDER",
                    Job.payload.contains({"order_id": order.id}),
                    Job.status.in_(["pending", "running"]),
                )
            )
            if existing.scalars().first():
                continue

            session.add(Job(job_type="CDEK_CREATE_ORDER", payload={"order_id": order.id}))
            created += 1

        await session.commit()
        logger.info("Created %s CDEK_CREATE_ORDER jobs from %s candidates", created, len(orders))
        return {"created": created, "candidates": len(orders)}
    finally:
        await session.close()


def main() -> None:
    result = asyncio.run(run())
    print(result)


if __name__ == "__main__":
    main()
