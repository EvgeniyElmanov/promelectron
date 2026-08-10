import hashlib
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.job import Job
from src.app.models.onec_sync import OnecIntakeLog
from src.app.services.storage_service import storage

# Hard 100 MB body limit for the 1С intake endpoint (D-04).
# Module-level constant so tests can monkeypatch it.
INTAKE_MAX_BODY_BYTES = 100 * 1024 * 1024

# Keep small payloads in memory, spill larger ones to a temp file.
_SPOOL_MAX_BYTES = 16 * 1024 * 1024

# Headers carrying credentials — never persisted in intake logs.
_SECRET_HEADERS = frozenset(
    {"x-1c-api-key", "authorization", "proxy-authorization", "cookie", "set-cookie"}
)


async def read_intake_body(
    request: Request,
) -> tuple[tempfile.SpooledTemporaryFile, int, str]:
    """Read the raw request body as a stream with an enforced size limit.

    Returns (file, received_bytes, sha256_hexdigest). The file is seeked to 0.
    Raises HTTPException(413) early on an oversized Content-Length, or during
    streaming when the actual body exceeds INTAKE_MAX_BODY_BYTES; in the latter
    case nothing is kept (the spool file is closed and discarded).
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            declared = 0
        if declared > INTAKE_MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Payload too large")

    sha256 = hashlib.sha256()
    received = 0
    body_file = tempfile.SpooledTemporaryFile(max_size=_SPOOL_MAX_BYTES)
    try:
        async for chunk in request.stream():
            sha256.update(chunk)
            received += len(chunk)
            if received > INTAKE_MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Payload too large")
            body_file.write(chunk)
    except Exception:
        body_file.close()
        raise
    body_file.seek(0)
    return body_file, received, sha256.hexdigest()


def make_object_key() -> str:
    """Object key `YYYY/MM/DD/HHmmss_<uuid4>.bin` in UTC (D-08)."""
    stamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/%H%M%S")
    return f"{stamp}_{uuid4()}.bin"


def _safe_headers(request: Request) -> dict[str, str]:
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _SECRET_HEADERS
    }


async def store_intake(session: AsyncSession, request: Request) -> OnecIntakeLog:
    """Store the raw request body in the intake bucket and log the metadata.

    Uploads to storage first; any storage error propagates and no DB row is
    written. The caller (endpoint) is responsible for commit (D-10).
    """
    body_file, received_bytes, sha256_hex = await read_intake_body(request)
    object_key = make_object_key()
    content_type = request.headers.get("content-type") or "application/octet-stream"
    bucket = settings.minio_intake_bucket

    try:
        await storage.upload_raw(object_key, body_file, content_type, bucket=bucket)
    finally:
        body_file.close()

    log = OnecIntakeLog(
        bucket=bucket,
        object_key=object_key,
        # Persist the same value that was sent to storage (fallback applied),
        # truncated to the column limit.
        content_type=content_type[:255],
        received_bytes=received_bytes,
        sha256=sha256_hex,
        headers=_safe_headers(request),
        query_params=dict(request.query_params),
        remote_addr=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:512] or None,
        status="received",
    )
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log


async def create_onec_intake_process_job(session: AsyncSession, intake_id: str) -> Job:
    """Enqueue an ONEC_INTAKE_PROCESS job for the given intake id.

    The caller (endpoint) is responsible for commit — the job lands in the
    same transaction as the intake log row.
    """
    job = Job(
        job_type="ONEC_INTAKE_PROCESS",
        payload={"intake_id": intake_id},
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job
