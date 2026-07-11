import json

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.schemas.onec import OnecWebhookPayload, OnecWebhookResponse
from src.app.services.onec_webhook_service import (
    compute_checksum,
    create_change_log,
    create_onec_apply_job,
    is_already_processed,
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

    return OnecWebhookResponse(
        status="accepted",
        batch_id=payload.batch_id,
    )
