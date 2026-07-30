"""AsyncIOScheduler: интервальная отправка pending changes (D-04, D-07)."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from onec_mock.config import Settings
from onec_mock.config import settings as default_settings
from onec_mock.db import async_session
from onec_mock.sender import Sender

logger = logging.getLogger("onec_mock.scheduler")


class SyncScheduler:
    """Interval job: collect pending → generate → send (регламентное задание 1С)."""

    def __init__(
        self,
        settings: Settings = default_settings,
        sender: Sender | None = None,
    ) -> None:
        self.settings = settings
        self.sender = sender or Sender(settings)
        self.scheduler = AsyncIOScheduler()
        self.last_run_at: datetime | None = None

    async def tick(self) -> None:
        """Один цикл отправки (также вызывается из POST /trigger/)."""
        async with async_session() as session:
            result = await self.sender.send_pending(session)
        self.last_run_at = datetime.now().astimezone()
        if result is None:
            logger.info("tick: nothing to send")
        else:
            logger.info("tick: batch %s -> %s", result.batch_id, result.status)

    def start(self) -> None:
        self.scheduler.add_job(
            self.tick,
            IntervalTrigger(minutes=self.settings.sync_interval_minutes),
            id="onec_sync",
            name="1C sync (pending changes -> intake)",
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()
        logger.info("scheduler started, interval=%s min", self.settings.sync_interval_minutes)

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    @property
    def running(self) -> bool:
        return self.scheduler.running

    @property
    def next_run_at(self) -> datetime | None:
        job = self.scheduler.get_job("onec_sync")
        return job.next_run_time if job else None
