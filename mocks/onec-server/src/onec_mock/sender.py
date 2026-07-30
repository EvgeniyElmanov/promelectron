"""Отправка CommerceML-пакетов на intake backend'а с retry/backoff (D-02, D-07).

Успех = HTTP 200/202 → change_log.batch_id проставляется, пишется sent_changes(success).
Сетевой сбой / не-2xx → sent_changes(failed), повтор по backoff (1/5/15 мин,
максимум 3 попытки на тик), пакет остаётся pending до следующего тика.
"""

import asyncio
import hashlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from onec_mock.commerceml import CommerceML2Generator, PackageGenerator
from onec_mock.config import Settings
from onec_mock.config import settings as default_settings
from onec_mock.models import ChangeLog, SentChanges

logger = logging.getLogger("onec_mock.sender")

BACKOFF_SECONDS = [60, 300, 900]  # 1 мин, 5 мин, 15 мин (D-07)
MAX_ATTEMPTS_PER_TICK = 3
RESPONSE_BODY_LIMIT = 2000
SUCCESS_STATUSES = {200, 202}
CORRUPT_CHECKSUM = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

# Защита от гонки «scheduler tick vs POST /trigger/» (F004): двойная отправка
# одних и тех же pending changes с разными batch_id недопустима. Сервис
# однопроцессный — достаточно общего asyncio.Lock.
send_lock = asyncio.Lock()


@dataclass
class SendResult:
    batch_id: str
    http_status: int | None
    status: str  # success | failed
    changes_sent: int
    checksum: str
    error: str | None = None


class Sender:
    def __init__(
        self,
        settings: Settings = default_settings,
        generator: PackageGenerator | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.generator = generator or CommerceML2Generator()
        self.sleep = sleep
        self._client = client

    async def _post(
        self, payload: bytes, batch_id: str, checksum: str
    ) -> tuple[int | None, str | None, str | None]:
        """POST пакета на intake. Возвращает (http_status, response_body, error)."""
        headers = {
            "X-1C-Api-Key": self.settings.onec_api_key,
            "Content-Type": "application/xml; charset=utf-8",
            "X-1C-Batch-Id": batch_id,
            "X-1C-Checksum": checksum,
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    self.settings.onec_target_url, content=payload, headers=headers
                )
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.settings.onec_target_url, content=payload, headers=headers
                    )
            return response.status_code, response.text[:RESPONSE_BODY_LIMIT], None
        except httpx.HTTPError as exc:
            return None, None, str(exc)

    async def _record(
        self,
        session: AsyncSession,
        batch_id: str,
        attempt: int,
        http_status: int | None,
        response_body: str | None,
        checksum: str,
        status: str,
        error: str | None,
        package_zip: bytes | None = None,
    ) -> None:
        session.add(
            SentChanges(
                batch_id=batch_id,
                attempt=attempt,
                sent_at=datetime.now(UTC),
                http_status=http_status,
                response_body=response_body,
                checksum=checksum,
                status=status,
                error=error,
                package_zip=package_zip,
            )
        )

    async def _send_with_retry(
        self,
        session: AsyncSession,
        payload: bytes,
        batch_id: str,
        changes_count: int,
        pending_ids: list[int] | None,
        corrupt_checksum: bool = False,
    ) -> SendResult:
        real_checksum = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        checksum = CORRUPT_CHECKSUM if corrupt_checksum else real_checksum
        last_status: int | None = None
        last_error: str | None = None

        for attempt in range(1, MAX_ATTEMPTS_PER_TICK + 1):
            http_status, response_body, error = await self._post(payload, batch_id, checksum)
            last_status, last_error = http_status, error
            if http_status in SUCCESS_STATUSES:
                if pending_ids:
                    await session.execute(
                        update(ChangeLog)
                        .where(ChangeLog.id.in_(pending_ids))
                        .values(batch_id=batch_id)
                    )
                await self._record(
                    session, batch_id, attempt, http_status, response_body,
                    checksum, "success", None, package_zip=payload,
                )
                await session.commit()
                logger.info("batch %s sent (attempt %s, http %s)", batch_id, attempt, http_status)
                return SendResult(batch_id, http_status, "success", changes_count, checksum)

            await self._record(
                session, batch_id, attempt, http_status, response_body,
                checksum, "failed", error or f"http {http_status}", package_zip=payload,
            )
            await session.commit()
            logger.warning(
                "batch %s attempt %s failed (http=%s, error=%s)", batch_id, attempt, http_status, error
            )
            if attempt < MAX_ATTEMPTS_PER_TICK:
                await self.sleep(BACKOFF_SECONDS[attempt - 1])

        # Попытки исчерпаны — изменения остаются pending до следующего тика (D-07)
        return SendResult(
            batch_id, last_status, "failed", changes_count, checksum,
            error=last_error or f"http {last_status}",
        )

    async def send_pending(
        self, session: AsyncSession, corrupt_checksum: bool = False
    ) -> SendResult | None:
        """Собрать pending changes → пакет → отправить. None, если нечего слать."""
        async with send_lock:
            changes = list(
                (
                    await session.execute(
                        select(ChangeLog)
                        .where(ChangeLog.batch_id.is_(None))
                        .order_by(ChangeLog.id)
                    )
                ).scalars()
            )
            if not changes:
                return None
            package = await self.generator.build(session, changes)
            return await self._send_with_retry(
                session,
                package.zip_bytes,
                batch_id=str(uuid.uuid4()),
                changes_count=len(changes),
                pending_ids=[c.id for c in changes],
                corrupt_checksum=corrupt_checksum,
            )

    async def resend_last(
        self, session: AsyncSession, corrupt_checksum: bool = False
    ) -> SendResult | None:
        """Повторно отправить последний успешный пакет (те же байты и batch_id).

        Сценарий duplicate_batch: проверяет идемпотентность intake/загрузчика.
        """
        last = (
            await session.execute(
                select(SentChanges)
                .where(SentChanges.status == "success", SentChanges.package_zip.isnot(None))
                .order_by(SentChanges.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last is None:
            return None
        async with send_lock:
            return await self._send_with_retry(
                session,
                last.package_zip,
                batch_id=last.batch_id,
                changes_count=0,
                pending_ids=None,
                corrupt_checksum=corrupt_checksum,
            )
