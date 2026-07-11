import pytest
from dataclasses import replace
from httpx import AsyncClient
from sqlalchemy import select

from src.app.core.config import settings
from src.app.models.job import Job


@pytest.mark.asyncio
async def test_admin_onec_full_sync(client: AsyncClient, admin_token: str, test_session, monkeypatch):
    patched = replace(
        settings,
        onec_api_url="http://1c.test",
        onec_default_supplier_id=1,
    )
    monkeypatch.setattr("src.app.api.admin.settings", patched)

    response = await client.post(
        "/api/v1/admin/onec/full-sync/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "queued"}

    result = await test_session.execute(select(Job).where(Job.job_type == "ONEC_FULL_SYNC"))
    job = result.scalar_one()
    assert job.status == "pending"


@pytest.mark.asyncio
async def test_admin_onec_full_sync_requires_admin(client: AsyncClient, user_token: str):
    response = await client.post(
        "/api/v1/admin/onec/full-sync/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_onec_full_sync_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/admin/onec/full-sync/")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_onec_full_sync_requires_config(client: AsyncClient, admin_token: str, monkeypatch):
    patched = replace(settings, onec_api_url=None, onec_default_supplier_id=None)
    monkeypatch.setattr("src.app.api.admin.settings", patched)

    response = await client.post(
        "/api/v1/admin/onec/full-sync/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 503
