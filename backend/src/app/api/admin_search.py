"""Admin API for catalog search (Phase 5, issue #121).

Attribute display management and the full reindex trigger. Admin-only;
Meilisearch master key stays on the server (D-03).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.attribute import (
    AttributeOut,
    AttributePatchOut,
    AttributeUpdate,
    ReindexJobOut,
)
from src.app.services import search_admin
from src.app.utils.auth import get_current_active_admin
from src.app.utils.rate_limiter import conditional_limit

router = APIRouter(tags=["admin-search"])


@router.get("/admin/attributes/", response_model=list[AttributeOut])
async def list_attributes(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список всех характеристик каталога с метаданными отображения."""
    return await search_admin.list_attributes(db)


@router.patch("/admin/attributes/{attribute_id}/", response_model=AttributePatchOut)
async def update_attribute(
    attribute_id: int,
    data: AttributeUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Правка is_filterable/name/unit/sort (code/value_type — мастер 1С).

    Изменение is_filterable НЕ применяется к Meilisearch «вживую»: новый
    набор filterable подхватит следующий full reindex (swap); в ответе —
    reindex_required=true, если набор изменился.
    """
    attribute, reindex_required = await search_admin.update_attribute(
        db, attribute_id, data
    )
    if attribute is None:
        raise HTTPException(status_code=404, detail="Attribute not found")
    out = AttributePatchOut.model_validate(attribute)
    out.reindex_required = reindex_required
    return out


@router.post(
    "/admin/search/reindex/",
    response_model=ReindexJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
@conditional_limit("5/minute")
async def trigger_full_reindex(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue полного swap-reindex'а (идемпотентно: 200 на повтор, 202 на новый)."""
    job, created = await search_admin.enqueue_full_reindex(db)
    if not created:
        response.status_code = status.HTTP_200_OK
    return ReindexJobOut(job_id=job.id, status=job.status, created=created)
