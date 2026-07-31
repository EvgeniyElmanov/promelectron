"""Meilisearch client and index provisioning (Phase 5, issue #121).

Decisions: D-02 (Meilisearch v1.50), D-03 (backend proxy, keys stay on the
server), D-04 (official sync SDK ``meilisearch==0.42.0``; async call sites use
``asyncio.to_thread``), D-06 (settings BEFORE documents; full reindex via
swap), D-11 (single index ``products``, primary key = internal ``Product.id``).

This module is the ONLY place that imports the Meilisearch SDK, so unit tests
can mock the whole client surface here. Indexing helpers (document build,
partial update, swap reindex) live in ``search_indexing.py``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable
from typing import Any

import meilisearch
from meilisearch.errors import MeilisearchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.attribute import Attribute

logger = logging.getLogger(__name__)

PRODUCTS_INDEX = "products"
PRODUCTS_INDEX_NEW = "products_new"
PRIMARY_KEY = "id"

# Base (non-EAV) fields. NB: ``brand`` is intentionally absent — the Product
# model has no brand column yet (PLAN.md R5 / open question Q2).
SEARCHABLE_ATTRIBUTES = ["name", "sku", "description"]
BASE_FILTERABLE_ATTRIBUTES = [
    "price",
    "stock",
    "category_id",
    "categories.lvl0",
    "categories.lvl1",
]
SORTABLE_ATTRIBUTES = ["price", "name", "id"]
# Default rules + ``stock:desc`` before ``sort``: in-stock products rank higher.
RANKING_RULES = [
    "words",
    "typo",
    "proximity",
    "attributeRank",
    "stock:desc",
    "sort",
    "wordPosition",
    "exactness",
]
# MVP synonym set (no Russian stemming in Meilisearch — D-02 compensation).
# Extension is a separate task (PLAN.md Q3).
SYNONYMS: dict[str, list[str]] = {
    "кабель": ["провод"],
    "провод": ["кабель"],
    "розетка": ["гнездо"],
    "автомат": ["выключатель автоматический"],
    "удлинитель": ["переноска"],
}


class SearchUnavailableError(RuntimeError):
    """Meilisearch is not configured or unreachable."""


class SearchTaskError(RuntimeError):
    """A Meilisearch async task failed or timed out."""


_client: meilisearch.Client | None = None


def get_meili_client() -> meilisearch.Client:
    """Return a lazily created sync Meilisearch client (D-04).

    Raises ``SearchUnavailableError`` when the service is not configured —
    call sites translate it into HTTP 503 instead of silently falling back.
    """
    global _client
    if _client is None:
        if not settings.meilisearch_url:
            raise SearchUnavailableError("Meilisearch is not configured (MEILISEARCH_URL)")
        _client = meilisearch.Client(
            settings.meilisearch_url, settings.meilisearch_master_key
        )
    return _client


def reset_meili_client() -> None:
    """Drop the cached client (test helper)."""
    global _client
    _client = None


def index_settings(filterable_attr_codes: Iterable[str]) -> dict[str, Any]:
    """Build the full index settings payload (D-06: apply BEFORE documents)."""
    filterable = BASE_FILTERABLE_ATTRIBUTES + [
        f"attrs.{code}" for code in filterable_attr_codes
    ]
    return {
        "searchableAttributes": SEARCHABLE_ATTRIBUTES,
        "filterableAttributes": filterable,
        "sortableAttributes": SORTABLE_ATTRIBUTES,
        "rankingRules": RANKING_RULES,
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {"oneTypo": 5, "twoTypos": 9},
            "disableOnNumbers": True,  # SKUs / article numbers
            "disableOnWords": [],
            "disableOnAttributes": [],
        },
        "faceting": {
            "maxValuesPerFacet": 100,
            "sortFacetValuesBy": {"*": "count"},
        },
        "pagination": {"maxTotalHits": 10000},
        "synonyms": SYNONYMS,
    }


async def get_filterable_attr_codes(db: AsyncSession) -> list[str]:
    """Return codes of attributes marked ``is_filterable`` in the catalog."""
    result = await db.execute(
        select(Attribute.code)
        .where(Attribute.is_filterable.is_(True))
        .order_by(Attribute.sort, Attribute.code)
    )
    return [row[0] for row in result.all()]


def provision_index(
    client: meilisearch.Client,
    index_uid: str,
    filterable_attr_codes: Iterable[str],
) -> None:
    """Create the index if missing and apply settings BEFORE documents (D-06).

    Called only from the swap-reindex flow — settings are never changed
    "live" on the serving index (spec Risks: filterableAttributes growth
    triggers reindexing in Meilisearch).
    """
    try:
        client.get_index(index_uid)
    except MeilisearchError:
        client.create_index(index_uid, {"primaryKey": PRIMARY_KEY})
    task = client.index(index_uid).update_settings(
        index_settings(filterable_attr_codes)
    )
    wait_for_task(client, task.task_uid)


def wait_for_task(
    client: meilisearch.Client,
    task_uid: int,
    timeout_seconds: float = 300.0,
    poll_interval: float = 0.5,
) -> None:
    """Poll ``GET /tasks/{uid}`` until succeeded; raise on failed/canceled/timeout."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        task = client.get_task(task_uid)
        status = task.status
        if status == "succeeded":
            return
        if status in ("failed", "canceled"):
            error = getattr(task, "error", None)
            raise SearchTaskError(f"Meilisearch task {task_uid} {status}: {error}")
        if time.monotonic() > deadline:
            raise SearchTaskError(
                f"Meilisearch task {task_uid} timed out after {timeout_seconds}s"
            )
        time.sleep(poll_interval)


# --- Async wrappers (D-04): sync SDK calls from async code via threads ---


async def search_async(
    client: meilisearch.Client,
    index_uid: str,
    query: str | None,
    opt_params: dict[str, Any],
) -> dict[str, Any]:
    return await asyncio.to_thread(client.index(index_uid).search, query, opt_params)


async def multi_search_async(
    client: meilisearch.Client, queries: list[dict[str, Any]]
) -> dict[str, Any]:
    return await asyncio.to_thread(client.multi_search, queries)


async def facet_search_async(
    client: meilisearch.Client,
    index_uid: str,
    facet_name: str,
    facet_query: str | None = None,
    opt_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    index = client.index(index_uid)
    return await asyncio.to_thread(
        index.facet_search, facet_name, facet_query, opt_params or {}
    )
