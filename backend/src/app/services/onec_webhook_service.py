import hashlib
import hmac

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.job import Job
from src.app.models.onec_sync import OnecChangeLog
from src.app.schemas.onec import OnecWebhookPayload


def validate_api_key(api_key: str | None) -> None:
    """Validate the X-1C-Api-Key header against the configured secret."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not hmac.compare_digest(api_key, settings.onec_webhook_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


def compute_checksum(payload_json: bytes) -> str:
    """Compute SHA256 checksum of the raw JSON payload."""
    return hashlib.sha256(payload_json).hexdigest()


async def is_already_processed(session: AsyncSession, checksum: str) -> bool:
    """Return True if a log with this checksum is already in progress or done.

    Failed logs are intentionally excluded so that a corrected payload can be
    retried by 1С.
    """
    result = await session.execute(
        select(OnecChangeLog).where(
            OnecChangeLog.checksum == checksum,
            OnecChangeLog.status.in_(["done", "pending", "processing"]),
        )
    )
    return result.scalar_one_or_none() is not None


async def create_change_log(
    session: AsyncSession,
    payload: OnecWebhookPayload,
    checksum: str,
    payload_json: bytes,
) -> OnecChangeLog:
    """Persist the incoming webhook payload as a pending OnecChangeLog row."""
    log = OnecChangeLog(
        batch_id=payload.batch_id,
        entity_type=payload.entity_type,
        source=payload.base_name,
        payload=payload.model_dump(mode="json"),
        payload_size_bytes=len(payload_json),
        status="pending",
        checksum=checksum,
    )
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log


async def create_onec_apply_job(session: AsyncSession, log_id: int) -> Job:
    """Enqueue an ONEC_APPLY_CHANGES job for the given change log id."""
    job = Job(
        job_type="ONEC_APPLY_CHANGES",
        payload={"log_id": log_id},
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job
