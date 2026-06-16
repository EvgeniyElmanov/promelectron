import os

from celery import Celery

from src.app.core.config import settings

os.environ.setdefault("PYTHONPATH", "src")

celery_app = Celery(
    "promelectron_workers",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.app.workers.tasks", "src.app.workers.cdek_tasks"],
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

# Schedule periodic tasks via beat
celery_app.conf.beat_schedule = {
    "sync-products-from-onec": {
        "task": "src.app.workers.tasks.sync_products_from_onec",
        "schedule": 300.0,  # every 5 minutes (override via env)
    },
}
