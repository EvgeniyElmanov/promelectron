"""Admin operations for catalog search (Phase 5, issue #121).

Attribute display management (``is_filterable``/``name``/``unit``/``sort``)
and the full reindex trigger. Changing ``is_filterable`` never touches
Meilisearch "live": the new filterable set is applied by the next
``SEARCH_REINDEX_FULL`` via swap (spec Risks / D-06).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.attribute import Attribute
from src.app.models.job import Job
from src.app.schemas.attribute import AttributeUpdate

REINDEX_JOB_TYPE = "SEARCH_REINDEX_FULL"


async def list_attributes(db: AsyncSession) -> list[Attribute]:
    result = await db.execute(
        select(Attribute).order_by(Attribute.sort, Attribute.code)
    )
    return list(result.scalars().all())


async def update_attribute(
    db: AsyncSession, attribute_id: int, data: AttributeUpdate
) -> tuple[Attribute | None, bool]:
    """Update display fields of an attribute.

    Returns ``(attribute, reindex_required)`` — the flag is set when the
    filterable set actually changed (``is_filterable`` toggled).
    """
    result = await db.execute(select(Attribute).where(Attribute.id == attribute_id))
    attribute = result.scalars().first()
    if attribute is None:
        return None, False

    reindex_required = False
    update = data.model_dump(exclude_unset=True)
    if "is_filterable" in update and update["is_filterable"] != attribute.is_filterable:
        reindex_required = True
    for field, value in update.items():
        setattr(attribute, field, value)
    await db.commit()
    await db.refresh(attribute)
    return attribute, reindex_required


async def enqueue_full_reindex(db: AsyncSession) -> tuple[Job, bool]:
    """Idempotently enqueue a full swap reindex (D-06).

    If a ``SEARCH_REINDEX_FULL`` job is already pending/running, return it
    instead of creating a duplicate.
    """
    result = await db.execute(
        select(Job)
        .where(Job.job_type == REINDEX_JOB_TYPE, Job.status.in_(["pending", "running"]))
        .order_by(Job.id)
        .limit(1)
    )
    existing = result.scalars().first()
    if existing is not None:
        return existing, False
    job = Job(job_type=REINDEX_JOB_TYPE, payload={})
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job, True
