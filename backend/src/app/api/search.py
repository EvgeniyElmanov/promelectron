"""Public catalog search API (Phase 5, issue #121, D-03/D-08/D-09).

Backend proxy to Meilisearch — keys never leave the server. All endpoints
are gated by the ``catalog_search_meilisearch`` feature flag (404 while the
flag is off; legacy ``GET /api/v1/products/`` stays untouched, D-09).

NB: the main endpoint parses repeating dynamic params (``attr.<code>``) from
``request.query_params``, which the ``@cache_response`` decorator cannot
pass through (it consumes the ``request`` kwarg) — so it applies the same
60s Redis caching manually with the decorator's key scheme.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.redis_client import redis_client
from src.app.db.database import get_db
from src.app.schemas.search import SearchResponse
from src.app.services import feature_flags, search_query
from src.app.services.search_query import SearchQueryError
from src.app.services.search_service import SearchUnavailableError
from src.app.utils.cache import build_cache_key, cache_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

SEARCH_FEATURE_FLAG = "catalog_search_meilisearch"


async def require_search_flag() -> None:
    """Gate all search endpoints behind the migration feature flag (D-09)."""
    if not await feature_flags.is_enabled(SEARCH_FEATURE_FLAG):
        raise HTTPException(status_code=404, detail="Not Found")


@router.get(
    "/",
    dependencies=[Depends(require_search_flag)],
    response_model=SearchResponse,
)
async def search_products(
    request: Request,
    q: str | None = None,
    category_id: int | None = None,
    page: int = Query(default=1, ge=1),
    hits_per_page: int = Query(default=20, ge=1, le=100),
    sort: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Catalog search with facets (OR inside a group / AND between groups)."""
    cache_key = build_cache_key(request)
    try:
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        pass  # Redis error — fall through to Meilisearch

    try:
        response = await search_query.search_products(
            db=db,
            q=q,
            category_id=category_id,
            page=page,
            hits_per_page=hits_per_page,
            sort=sort,
            price_min=price_min,
            price_max=price_max,
            query_params=request.query_params,
        )
    except (SearchQueryError, SearchUnavailableError) as exc:
        raise search_query.map_search_errors(exc) from exc

    try:
        await redis_client.set(
            cache_key,
            json.dumps(jsonable_encoder(response)),
            search_query.SEARCH_CACHE_TTL_SECONDS,
        )
    except Exception:
        pass  # Redis error — response is still returned

    return response


@router.get("/suggestions/", dependencies=[Depends(require_search_flag)])
@cache_response(ttl_seconds=60)
async def search_suggestions(
    q: str | None = None,
    limit: int = Query(default=10, ge=1, le=10),
):
    """Search box suggestions (contract matches useSearchSuggestions.ts)."""
    try:
        return await search_query.search_suggestions(q=q, limit=limit)
    except SearchUnavailableError as exc:
        raise search_query.map_search_errors(exc) from exc


@router.get("/facet-values/", dependencies=[Depends(require_search_flag)])
@cache_response(ttl_seconds=60)
async def search_facet_values(
    facet: str,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Search values of long enum facets (proxy to facet-search API)."""
    try:
        return await search_query.search_facet_values(db=db, facet=facet, q=q)
    except (SearchQueryError, SearchUnavailableError) as exc:
        raise search_query.map_search_errors(exc) from exc
