"""Тесты sender'а: retry/backoff, журнал sent_changes (D-02, D-07)."""

import httpx
from sqlalchemy import func, select

from onec_mock.config import settings
from onec_mock.models import ChangeLog, SentChanges
from onec_mock.scenarios import run_scenario
from onec_mock.sender import BACKOFF_SECONDS, Sender


class FakeClock:
    def __init__(self):
        self.sleeps: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.sleeps.append(seconds)


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(202, json={"intake_id": "abc", "received_bytes": 123})


def _fail(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="boom")


async def _seed_pending(session):
    await run_scenario(session, settings, "normal", {})


async def test_success_marks_batch_and_records(seeded_session):
    clock = FakeClock()
    client = _client(_ok)
    sender = Sender(settings, sleep=clock, client=client)
    await _seed_pending(seeded_session)

    result = await sender.send_pending(seeded_session)

    assert result is not None
    assert result.status == "success"
    assert result.http_status == 202
    assert result.checksum.startswith("sha256:")
    pending = await seeded_session.scalar(
        select(func.count(ChangeLog.id)).where(ChangeLog.batch_id.is_(None))
    )
    assert pending == 0
    sent = await seeded_session.scalar(
        select(func.count(SentChanges.id)).where(
            SentChanges.batch_id == result.batch_id, SentChanges.status == "success"
        )
    )
    assert sent == 1
    assert clock.sleeps == []
    await client.aclose()


async def test_request_headers_follow_contract(seeded_session):
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(202, text="ok")

    client = _client(handler)
    sender = Sender(settings, sleep=FakeClock(), client=client)
    await _seed_pending(seeded_session)

    result = await sender.send_pending(seeded_session)

    assert result.status == "success"
    headers = captured[0].headers
    assert headers["X-1C-Api-Key"] == settings.onec_api_key
    assert headers["Content-Type"] == "application/xml; charset=utf-8"
    assert headers["X-1C-Batch-Id"] == result.batch_id
    assert headers["X-1C-Checksum"] == result.checksum
    await client.aclose()


async def test_http_500_retries_with_backoff_and_keeps_pending(seeded_session):
    clock = FakeClock()
    client = _client(_fail)
    sender = Sender(settings, sleep=clock, client=client)
    await _seed_pending(seeded_session)

    result = await sender.send_pending(seeded_session)

    assert result.status == "failed"
    assert result.http_status == 500
    assert clock.sleeps == BACKOFF_SECONDS[:2]  # 1 мин, 5 мин; после 3-й попытки не ждём
    fails = await seeded_session.scalar(
        select(func.count(SentChanges.id)).where(
            SentChanges.batch_id == result.batch_id, SentChanges.status == "failed"
        )
    )
    assert fails == 3
    pending = await seeded_session.scalar(
        select(func.count(ChangeLog.id)).where(ChangeLog.batch_id.is_(None))
    )
    assert pending == result.changes_sent
    await client.aclose()


async def test_network_error_recorded_as_failed(seeded_session):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    clock = FakeClock()
    client = _client(handler)
    sender = Sender(settings, sleep=clock, client=client)
    await _seed_pending(seeded_session)

    result = await sender.send_pending(seeded_session)

    assert result.status == "failed"
    assert result.http_status is None
    assert "connection refused" in (result.error or "")
    errors = await seeded_session.scalar(
        select(func.count(SentChanges.id)).where(
            SentChanges.batch_id == result.batch_id,
            SentChanges.status == "failed",
            SentChanges.error.isnot(None),
        )
    )
    assert errors == 3
    await client.aclose()


async def test_resend_last_sends_same_bytes_and_batch_id(seeded_session):
    bodies: list[bytes] = []
    batch_ids: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content)
        batch_ids.append(request.headers["X-1C-Batch-Id"])
        return httpx.Response(202, text="ok")

    client = _client(handler)
    sender = Sender(settings, sleep=FakeClock(), client=client)
    await _seed_pending(seeded_session)

    first = await sender.send_pending(seeded_session)
    duplicate = await sender.resend_last(seeded_session)

    assert duplicate is not None
    assert duplicate.batch_id == first.batch_id
    assert len(bodies) == 2
    assert bodies[0] == bodies[1]  # байт-в-байт тот же пакет (duplicate_batch)
    assert batch_ids[0] == batch_ids[1]
    await client.aclose()


async def test_bad_checksum_sends_corrupt_header(seeded_session):
    checksums: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        checksums.append(request.headers["X-1C-Checksum"])
        return httpx.Response(202, text="ok")

    client = _client(handler)
    sender = Sender(settings, sleep=FakeClock(), client=client)
    await _seed_pending(seeded_session)

    result = await sender.send_pending(seeded_session, corrupt_checksum=True)

    assert result.status == "success"
    assert result.checksum != f"sha256:{__import__('hashlib').sha256(b'').hexdigest()}"
    assert checksums[0] == result.checksum
    # checksum заведомо неверен для тела пакета
    import hashlib

    assert result.checksum.startswith("sha256:0000")
    assert result.checksum != f"sha256:{hashlib.sha256(result.batch_id.encode()).hexdigest()}"
    await client.aclose()


async def test_nothing_pending_returns_none(seeded_session):
    client = _client(_ok)
    sender = Sender(settings, sleep=FakeClock(), client=client)

    result = await sender.send_pending(seeded_session)

    assert result is None
    await client.aclose()
