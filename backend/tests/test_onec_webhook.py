from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.app.core.config import settings
from src.app.models.job import Job
from src.app.models.onec_sync import OnecChangeLog


@pytest.fixture
def onec_api_key():
    return "test-onec-webhook-key"


@pytest.fixture(autouse=True)
def patch_onec_webhook_key(monkeypatch, onec_api_key):
    monkeypatch.setattr(
        "src.app.services.onec_webhook_service.settings",
        replace(settings, onec_webhook_api_key=onec_api_key),
    )


def _build_payload():
    return {
        "batch_id": str(uuid4()),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "base_name": "test-base",
        "entity_type": "product",
        "changes": [
            {
                "external_id": "1c-product-1",
                "action": "create",
                "version": datetime.now(timezone.utc).isoformat(),
                "data": {"name": "1C Product", "price": 199.99, "stock": 5},
            }
        ],
    }


@pytest.mark.asyncio
async def test_onec_webhook_success(client: AsyncClient, test_session, onec_api_key):
    payload = _build_payload()

    response = await client.post(
        "/api/v1/onec/webhook/",
        json=payload,
        headers={"X-1C-Api-Key": onec_api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["batch_id"] == payload["batch_id"]

    result = await test_session.execute(select(OnecChangeLog))
    log = result.scalar_one()
    assert log.entity_type == "product"
    assert log.status == "pending"
    assert log.checksum and len(log.checksum) == 64

    result = await test_session.execute(select(Job))
    job = result.scalar_one()
    assert job.job_type == "ONEC_APPLY_CHANGES"
    assert job.payload == {"log_id": log.id}


@pytest.mark.asyncio
async def test_onec_webhook_invalid_key(client: AsyncClient):
    response = await client.post(
        "/api/v1/onec/webhook/",
        json=_build_payload(),
        headers={"X-1C-Api-Key": "wrong-key"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_onec_webhook_deduplication(client: AsyncClient, test_session, onec_api_key):
    payload = _build_payload()

    response = await client.post(
        "/api/v1/onec/webhook/",
        json=payload,
        headers={"X-1C-Api-Key": onec_api_key},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    # Simulate successful processing of the first batch.
    result = await test_session.execute(select(OnecChangeLog))
    log = result.scalar_one()
    log.status = "done"
    await test_session.commit()

    response = await client.post(
        "/api/v1/onec/webhook/",
        json=deepcopy(payload),
        headers={"X-1C-Api-Key": onec_api_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "already_processed"
    assert data["batch_id"] == payload["batch_id"]

    result = await test_session.execute(select(OnecChangeLog))
    logs = result.scalars().all()
    assert len(logs) == 1

    result = await test_session.execute(select(Job).where(Job.job_type == "ONEC_APPLY_CHANGES"))
    jobs = result.scalars().all()
    assert len(jobs) == 1


@pytest.mark.asyncio
async def test_onec_webhook_invalid_payload(client: AsyncClient, onec_api_key):
    response = await client.post(
        "/api/v1/onec/webhook/",
        json={"entity_type": "product"},
        headers={"X-1C-Api-Key": onec_api_key},
    )
    assert response.status_code == 422
