import os

from celery import Celery

from src.app.core.config import settings

os.environ.setdefault("PYTHONPATH", "src")

celery_app = Celery(
    "promelectron_workers",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
)

# NOTE: legacy 1C sync Celery task was removed. CDEK and 1C flows now use
# the async job_worker and the ``jobs`` table.
