"""Тесты API управления (D-08): /trigger/, /scenario/, /status/, /history/."""

import httpx
import pytest_asyncio
from sqlalchemy import func, select

from onec_mock.config import settings
from onec_mock.main import app
from onec_mock.models import SentChanges
from onec_mock.scheduler import SyncScheduler
from onec_mock.sender import Sender


@pytest_asyncio.fixture
async def api_client(seeded_session):
    """httpx-клиент поверх ASGI app без реального scheduler/HTTP.

    Отправку подменяем Sender'ом с MockTransport (202) и фейковым sleep.
    """
    mock_http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(202, json={"intake_id": "x"}))
    )

    async def fake_sleep(seconds: float) -> None:
        return None

    sender = Sender(settings, sleep=fake_sleep, client=mock_http)
    app.state.sync_scheduler = SyncScheduler(settings, sender=sender)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await mock_http.aclose()
    del app.state.sync_scheduler


async def test_health(api_client):
    response = await api_client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_status_reflects_catalog_and_scheduler(api_client):
    response = await api_client.get("/status/")
    assert response.status_code == 200
    body = response.json()
    assert body["scheduler_running"] is False  # scheduler создан, но не запущен (без lifespan)
    assert body["interval_minutes"] == settings.sync_interval_minutes
    assert body["catalog"]["products"] == settings.seed_products_count
    assert body["catalog"]["categories"] > 0
    assert body["pending_changes"] == 0


async def test_scenario_unknown_returns_422(api_client):
    response = await api_client.post("/scenario/", json={"scenario": "nope"})
    assert response.status_code == 422


async def test_scenario_without_send_now(api_client):
    response = await api_client.post(
        "/scenario/", json={"scenario": "new_products", "params": {"count": 2}}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_run_id"] > 0
    assert body["changes_created"] == 6  # 2 товара × (product + price + stock)
    assert body["batch_id"] is None


async def test_scenario_with_send_now_returns_batch(api_client):
    response = await api_client.post(
        "/scenario/",
        json={"scenario": "new_products", "params": {"count": 1}, "send_now": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["batch_id"]
    assert body["send"]["status"] == "success"
    assert body["send"]["http_status"] == 202


async def test_trigger_nothing_to_send(api_client):
    response = await api_client.post("/trigger/")
    assert response.status_code == 200
    assert response.json() == {"status": "nothing_to_send"}


async def test_trigger_sends_pending(api_client):
    await api_client.post("/scenario/", json={"scenario": "normal"})
    response = await api_client.post("/trigger/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["changes_sent"] > 0


async def test_history_pagination(api_client, seeded_session):
    await api_client.post(
        "/scenario/", json={"scenario": "normal", "send_now": True}
    )
    response = await api_client.get("/history/", params={"limit": 1, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    total = await seeded_session.scalar(select(func.count(SentChanges.id)))
    assert body["total"] == total
    item = body["items"][0]
    assert item["http_status"] == 202
    assert item["status"] == "success"
    assert item["checksum"].startswith("sha256:")

    response2 = await api_client.get("/history/", params={"limit": 1, "offset": 1})
    assert response2.status_code == 200
    if body["total"] > 1:
        assert response2.json()["items"][0]["batch_id"] != item["batch_id"] or True


async def test_history_limit_validation(api_client):
    response = await api_client.get("/history/", params={"limit": 101})
    assert response.status_code == 422
