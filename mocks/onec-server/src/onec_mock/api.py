"""API управления мок-сервера 1С (D-08).

Без auth — сервис не публикуется через ingress (только ClusterIP), в prod
отключён (onecMock.enabled=false). Инструмент разработки/демо.
Trailing slash обязателен во всех endpoint'ах (инвариант проекта).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onec_mock.config import settings
from onec_mock.db import get_session
from onec_mock.models import Category, ChangeLog, Product, SentChanges
from onec_mock.scenarios import Scenario, run_scenario
from onec_mock.sender import Sender, SendResult

logger = logging.getLogger("onec_mock.api")

router = APIRouter(tags=["onec-mock-control"])


class ScenarioRequest(BaseModel):
    scenario: Scenario
    params: dict = Field(default_factory=dict)
    send_now: bool = False


def _get_sender(request: Request) -> Sender:
    sync_scheduler = getattr(request.app.state, "sync_scheduler", None)
    if sync_scheduler is not None:
        return sync_scheduler.sender
    return Sender(settings)


async def _send_for_scenario(
    session: AsyncSession, sender: Sender, scenario: Scenario
) -> SendResult | None:
    """Отправка с учётом special-сценариев duplicate_batch / bad_checksum (D-06)."""
    if scenario is Scenario.duplicate_batch:
        return await sender.resend_last(session)
    if scenario is Scenario.bad_checksum:
        result = await sender.send_pending(session, corrupt_checksum=True)
        if result is None:  # нет pending — портим checksum последнего пакета
            result = await sender.resend_last(session, corrupt_checksum=True)
        return result
    return await sender.send_pending(session)


def _send_result_payload(result: SendResult | None) -> dict:
    if result is None:
        return {"status": "nothing_to_send"}
    return {
        "batch_id": result.batch_id,
        "http_status": result.http_status,
        "status": result.status,
        "changes_sent": result.changes_sent,
        "checksum": result.checksum,
        "error": result.error,
    }


@router.post("/trigger/")
async def trigger(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    """Форс-отправка pending changes вне расписания."""
    sender = _get_sender(request)
    result = await sender.send_pending(session)
    return _send_result_payload(result)


@router.post("/scenario/")
async def scenario(
    body: ScenarioRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Запустить сценарий мутаций (неизвестный сценарий → 422 от pydantic)."""
    run = await run_scenario(session, settings, body.scenario.value, body.params)
    payload: dict = {
        "scenario_run_id": run.id,
        "changes_created": run.changes_created,
        "batch_id": None,
    }
    if body.send_now:
        sender = _get_sender(request)
        result = await _send_for_scenario(session, sender, body.scenario)
        if result is not None:
            payload["batch_id"] = result.batch_id
            payload["send"] = _send_result_payload(result)
    return payload


@router.get("/status/")
async def status(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    """Состояние планировщика и каталога."""
    sync_scheduler = getattr(request.app.state, "sync_scheduler", None)
    pending = await session.scalar(
        select(func.count(ChangeLog.id)).where(ChangeLog.batch_id.is_(None))
    )
    products = await session.scalar(select(func.count(Product.id)))
    categories = await session.scalar(select(func.count(Category.id)))
    return {
        "scheduler_running": bool(sync_scheduler and sync_scheduler.running),
        "interval_minutes": settings.sync_interval_minutes,
        "last_run_at": (
            sync_scheduler.last_run_at.isoformat()
            if sync_scheduler and sync_scheduler.last_run_at
            else None
        ),
        "next_run_at": (
            sync_scheduler.next_run_at.isoformat()
            if sync_scheduler and sync_scheduler.next_run_at
            else None
        ),
        "pending_changes": pending or 0,
        "catalog": {"products": products or 0, "categories": categories or 0},
    }


@router.get("/history/")
async def history(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """История отправок из sent_changes (пагинация limit/offset)."""
    total = await session.scalar(select(func.count(SentChanges.id)))
    rows = (
        await session.execute(
            select(SentChanges)
            .order_by(SentChanges.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars()
    rows = list(rows)
    # changes_count одним GROUP BY-запросом (без N+1, F010)
    batch_ids = [row.batch_id for row in rows]
    counts: dict[str, int] = {}
    if batch_ids:
        count_rows = await session.execute(
            select(ChangeLog.batch_id, func.count())
            .where(ChangeLog.batch_id.in_(batch_ids))
            .group_by(ChangeLog.batch_id)
        )
        counts = {batch_id: count for batch_id, count in count_rows.all()}
    items = []
    for row in rows:
        items.append(
            {
                "batch_id": row.batch_id,
                "sent_at": row.sent_at.isoformat(),
                "attempt": row.attempt,
                "http_status": row.http_status,
                "status": row.status,
                "checksum": row.checksum,
                "changes_count": counts.get(row.batch_id, 0),
                "error": row.error,
            }
        )
    return {"items": items, "total": total or 0}
