import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.schemas.onec import OnecIntakeResponse, OnecWebhookPayload, OnecWebhookResponse
from src.app.services.onec_intake_service import (
    create_onec_intake_process_job,
    store_intake,
)
from src.app.services.onec_webhook_service import (
    compute_checksum,
    create_change_log,
    create_onec_apply_job,
    is_already_processed,
    is_batch_already_exists,
    validate_api_key,
)
from src.app.utils.rate_limiter import conditional_limit

router = APIRouter(prefix="/onec", tags=["onec"])


@router.post("/webhook/", response_model=OnecWebhookResponse)
@conditional_limit("100/minute")
async def onec_webhook(
    request: Request,
    payload: OnecWebhookPayload,
    x_1c_api_key: str | None = Header(default=None, alias="X-1C-Api-Key"),
    db: AsyncSession = Depends(get_db),
):
    validate_api_key(x_1c_api_key)

    if await is_batch_already_exists(db, str(payload.batch_id)):
        return OnecWebhookResponse(
            status="already_processed",
            batch_id=payload.batch_id,
        )

    payload_json = json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    checksum = compute_checksum(payload_json)

    if await is_already_processed(db, checksum):
        return OnecWebhookResponse(
            status="already_processed",
            batch_id=payload.batch_id,
        )

    log = await create_change_log(db, payload, checksum, payload_json)
    await create_onec_apply_job(db, log.id)
    await db.commit()

    return OnecWebhookResponse(
        status="accepted",
        batch_id=payload.batch_id,
    )


@router.post("/intake/", response_model=OnecIntakeResponse, status_code=202)
# Known limitation: the limiter keys on request.client.host, which behind
# nginx-ingress is the ingress pod IP, not the real client (same trade-off as
# /onec/webhook/). Moving to X-Forwarded-For from a trusted proxy is a
# separate follow-up task.
@conditional_limit("100/minute")
async def onec_intake(
    request: Request,
    x_1c_api_key: str | None = Header(default=None, alias="X-1C-Api-Key"),
    x_1c_checksum: str | None = Header(default=None, alias="X-1C-Checksum"),
    db: AsyncSession = Depends(get_db),
):
    validate_api_key(x_1c_api_key)

    log = await store_intake(db, request, expected_checksum=x_1c_checksum)
    if log.status == "failed":
        # Checksum mismatch: фиксируем отказ в onec_intake_log (коммитим),
        # job разбора НЕ создаём — сырое тело остаётся в MinIO для форензики.
        await db.commit()
        raise HTTPException(status_code=400, detail="X-1C-Checksum mismatch")
    await create_onec_intake_process_job(db, str(log.intake_id))
    await db.commit()

    return OnecIntakeResponse(
        intake_id=log.intake_id,
        received_bytes=log.received_bytes,
    )
