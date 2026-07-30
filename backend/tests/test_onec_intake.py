import hashlib
import re
from dataclasses import replace
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.app.core.config import settings
from src.app.models.onec_sync import OnecIntakeLog


class FakeIntakeStorage:
    """In-memory storage capturing upload_raw calls."""

    def __init__(self):
        self.objects = {}

    async def upload_raw(self, key, data, content_type, bucket=None):
        content = data if isinstance(data, bytes) else data.read()
        self.objects[(bucket, key)] = content
        return f"fake://{bucket}/{key}"


@pytest.fixture
def onec_api_key():
    return "test-onec-intake-key"


@pytest.fixture(autouse=True)
def patch_onec_webhook_key(monkeypatch, onec_api_key):
    monkeypatch.setattr(
        "src.app.services.onec_webhook_service.settings",
        replace(settings, onec_webhook_api_key=onec_api_key),
    )


@pytest.fixture
def fake_storage(monkeypatch):
    storage = FakeIntakeStorage()
    monkeypatch.setattr("src.app.services.onec_intake_service.storage", storage)
    return storage


@pytest.mark.asyncio
async def test_intake_success_json(
    client: AsyncClient, test_session, fake_storage, onec_api_key
):
    body = b'{"ref_key": "abc", "value": 123}'
    response = await client.post(
        "/api/v1/onec/intake/?source=ut11&kind=catalog",
        content=body,
        headers={
            "X-1C-Api-Key": onec_api_key,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert data["received_bytes"] == len(body)
    intake_id = UUID(data["intake_id"])

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    assert log.intake_id == intake_id
    assert log.status == "received"
    assert log.bucket == "onec-intake"
    assert log.content_type == "application/json"
    assert log.received_bytes == len(body)
    assert log.sha256 == hashlib.sha256(body).hexdigest()
    assert log.query_params == {"source": "ut11", "kind": "catalog"}
    assert "x-1c-api-key" not in {k.lower() for k in log.headers}
    assert log.headers.get("content-type") == "application/json"

    stored = fake_storage.objects[(log.bucket, log.object_key)]
    assert stored == body


@pytest.mark.asyncio
async def test_intake_secret_headers_not_persisted(
    client: AsyncClient, test_session, fake_storage, onec_api_key
):
    """authorization/proxy-authorization/cookie must not land in the JSONB log."""
    response = await client.post(
        "/api/v1/onec/intake/",
        content=b"data",
        headers={
            "X-1C-Api-Key": onec_api_key,
            "Authorization": "Bearer secret-jwt-token",
            "Proxy-Authorization": "Basic cHJveHk6c2VjcmV0",
            "Cookie": "session=secret-cookie",
        },
    )

    assert response.status_code == 202

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    persisted = {k.lower() for k in log.headers}
    assert "authorization" not in persisted
    assert "proxy-authorization" not in persisted
    assert "cookie" not in persisted
    assert "set-cookie" not in persisted
    assert "x-1c-api-key" not in persisted
    assert not any("secret" in str(v) for v in log.headers.values())


@pytest.mark.asyncio
async def test_intake_long_headers_truncated(
    client: AsyncClient, test_session, fake_storage, onec_api_key
):
    """content_type/user_agent are truncated to the column limits, no 500."""
    response = await client.post(
        "/api/v1/onec/intake/",
        content=b"data",
        headers={
            "X-1C-Api-Key": onec_api_key,
            "Content-Type": "application/" + "x" * 300,
            "User-Agent": "UA-" + "y" * 600,
        },
    )

    assert response.status_code == 202

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    assert len(log.content_type) == 255
    assert len(log.user_agent) == 512


@pytest.mark.asyncio
async def test_intake_success_binary(
    client: AsyncClient, test_session, fake_storage, onec_api_key
):
    body = bytes(range(256)) + b"\x00\x00\xff binary \x01\x02"
    response = await client.post(
        "/api/v1/onec/intake/",
        content=body,
        headers={
            "X-1C-Api-Key": onec_api_key,
            "Content-Type": "application/octet-stream",
        },
    )

    assert response.status_code == 202
    assert response.json()["received_bytes"] == len(body)

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    assert fake_storage.objects[(log.bucket, log.object_key)] == body
    assert log.sha256 == hashlib.sha256(body).hexdigest()


@pytest.mark.asyncio
async def test_intake_success_xml(
    client: AsyncClient, fake_storage, onec_api_key, test_session
):
    body = '<?xml version="1.0" encoding="UTF-8"?><КоммерческаяИнформация/>'.encode("utf-8")
    response = await client.post(
        "/api/v1/onec/intake/",
        content=body,
        headers={"X-1C-Api-Key": onec_api_key, "Content-Type": "application/xml"},
    )

    assert response.status_code == 202

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    assert fake_storage.objects[(log.bucket, log.object_key)] == body


@pytest.mark.asyncio
async def test_intake_no_content_type(
    client: AsyncClient, fake_storage, onec_api_key, test_session
):
    body = b"raw bytes without content type"
    response = await client.post(
        "/api/v1/onec/intake/",
        content=body,
        headers={"X-1C-Api-Key": onec_api_key, "Content-Type": ""},
    )

    assert response.status_code == 202

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    # The same fallback value that went to storage is persisted in the DB.
    assert log.content_type == "application/octet-stream"
    assert fake_storage.objects[(log.bucket, log.object_key)] == body


@pytest.mark.asyncio
async def test_intake_empty_body(
    client: AsyncClient, fake_storage, onec_api_key, test_session
):
    response = await client.post(
        "/api/v1/onec/intake/",
        content=b"",
        headers={"X-1C-Api-Key": onec_api_key},
    )

    assert response.status_code == 202
    assert response.json()["received_bytes"] == 0

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    assert log.sha256 == hashlib.sha256(b"").hexdigest()
    assert fake_storage.objects[(log.bucket, log.object_key)] == b""


@pytest.mark.asyncio
async def test_intake_missing_key(client: AsyncClient):
    response = await client.post("/api/v1/onec/intake/", content=b"data")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_intake_invalid_key(client: AsyncClient):
    response = await client.post(
        "/api/v1/onec/intake/",
        content=b"data",
        headers={"X-1C-Api-Key": "wrong-key"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_intake_body_exceeds_limit(
    client: AsyncClient, test_session, fake_storage, onec_api_key, monkeypatch
):
    monkeypatch.setattr(
        "src.app.services.onec_intake_service.INTAKE_MAX_BODY_BYTES", 10
    )
    body = b"x" * 100

    response = await client.post(
        "/api/v1/onec/intake/",
        content=body,
        headers={"X-1C-Api-Key": onec_api_key},
    )

    assert response.status_code == 413
    assert fake_storage.objects == {}
    result = await test_session.execute(select(OnecIntakeLog))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_intake_early_reject_by_content_length(onec_api_key):
    """Content-Length above the limit is rejected before reading the body."""
    from fastapi import HTTPException

    from src.app.services import onec_intake_service

    class FakeRequest:
        def __init__(self):
            self.headers = {
                "content-length": str(onec_intake_service.INTAKE_MAX_BODY_BYTES + 1)
            }
            self.read = False

        async def stream(self):
            self.read = True
            yield b"data"

    request = FakeRequest()
    with pytest.raises(HTTPException) as exc_info:
        await onec_intake_service.read_intake_body(request)
    assert exc_info.value.status_code == 413
    assert request.read is False


@pytest.mark.asyncio
async def test_intake_stream_overrun_by_fact(monkeypatch):
    """Body that exceeds the limit mid-stream is rejected; nothing is kept."""
    from fastapi import HTTPException

    from src.app.services import onec_intake_service

    monkeypatch.setattr(onec_intake_service, "INTAKE_MAX_BODY_BYTES", 10)

    class FakeRequest:
        headers = {}

        async def stream(self):
            yield b"12345"
            yield b"67890"
            yield b"overflow"

    with pytest.raises(HTTPException) as exc_info:
        await onec_intake_service.read_intake_body(FakeRequest())
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_intake_object_key_format(
    client: AsyncClient, test_session, fake_storage, onec_api_key
):
    response = await client.post(
        "/api/v1/onec/intake/",
        content=b"data",
        headers={"X-1C-Api-Key": onec_api_key},
    )
    assert response.status_code == 202

    result = await test_session.execute(select(OnecIntakeLog))
    log = result.scalar_one()
    assert re.fullmatch(
        r"\d{4}/\d{2}/\d{2}/\d{6}_[0-9a-f-]{36}\.bin", log.object_key
    )
    assert (log.bucket, log.object_key) in fake_storage.objects
