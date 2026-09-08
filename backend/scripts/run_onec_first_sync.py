"""Разовый прогон ONEC full sync против локального OData-мока (issue #227).

Вызывает run_onec_full_sync и затем синхронно обрабатывает поставленные
ONEC_APPLY_CHANGES job'ы. Не для продакшена — инструмент первичной загрузки.
"""

import asyncio
import logging

from sqlalchemy import select

from src.app.db.database import SessionLocal
from src.app.models.job import Job
from src.app.services.onec_sync_service import run_onec_full_sync
from src.app.workers.job_worker import handle_onec_apply_changes_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("onec-first-sync")


async def main() -> None:
    async with SessionLocal() as db:
        await run_onec_full_sync(db, default_supplier_id=1)
        await db.commit()
        logger.info("full sync fetch done, jobs enqueued")

    done = failed = 0
    while True:
        async with SessionLocal() as db:
            result = await db.execute(
                select(Job)
                .where(Job.job_type == "ONEC_APPLY_CHANGES", Job.status == "pending")
                .order_by(Job.id)
                .limit(1)
            )
            job = result.scalar_one_or_none()
            if job is None:
                break
            try:
                await handle_onec_apply_changes_job(job, db)
                job.status = "done"
                done += 1
            except Exception:
                job.status = "failed"
                failed += 1
                logger.exception("job %s failed", job.id)
            await db.commit()
        if (done + failed) % 20 == 0:
            logger.info("jobs processed: done=%d failed=%d", done, failed)

    logger.info("DONE: done=%d failed=%d", done, failed)


if __name__ == "__main__":
    asyncio.run(main())
