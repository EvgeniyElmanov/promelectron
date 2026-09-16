"""Search document build and indexing pipeline (Phase 5, issue #121).

Decisions: D-06 (partial update via jobs; full reindex via swap indexes),
D-07 (adjacency-list categories denormalized into ``categories.lvl0/lvl1``),
D-10 (typed attribute values: number/bool/text), D-11 (document shape,
primary key = internal ``Product.id``).

All Meilisearch SDK calls here are SYNC and must be invoked from async code
via ``asyncio.to_thread`` (D-04) — the job worker and API share one event
loop and must not be blocked for the duration of a full reindex.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import meilisearch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.attribute import Attribute, ProductAttributeValue
from src.app.models.category import Category
from src.app.models.product import Product
from src.app.services.product_aggregates import BRAND_ATTRIBUTE_NAME, normalize_brand_value
from src.app.services.search_service import (
    PRODUCTS_INDEX,
    PRODUCTS_INDEX_NEW,
    ensure_index_exists,
    get_filterable_attr_codes,
    provision_index,
    wait_for_task,
)

logger = logging.getLogger(__name__)

PARTIAL_BATCH_SIZE = 1000
REINDEX_BATCH_SIZE = 10000


async def _load_category_paths(
    db: AsyncSession, category_ids: Iterable[int]
) -> dict[int, tuple[Category, Category | None]]:
    """Load categories and their parents (2 levels, D-07) without N+1.

    Returns ``{category_id: (category, parent_or_none)}``.
    """
    ids = {cid for cid in category_ids if cid is not None}
    if not ids:
        return {}
    result = await db.execute(select(Category).where(Category.id.in_(ids)))
    categories = {c.id: c for c in result.scalars().all()}
    parent_ids = {c.parent_id for c in categories.values() if c.parent_id}
    parents: dict[int, Category] = {}
    if parent_ids:
        result = await db.execute(select(Category).where(Category.id.in_(parent_ids)))
        parents = {c.id: c for c in result.scalars().all()}
    return {
        cid: (cat, parents.get(cat.parent_id)) for cid, cat in categories.items()
    }


async def _load_attribute_values(
    db: AsyncSession, product_ids: list[int]
) -> dict[int, dict[str, Any]]:
    """Load typed attribute values for products in one query (no N+1, PLAN R2).

    Returns ``{product_id: {attr_code: typed_value}}`` (D-10).
    """
    if not product_ids:
        return {}
    result = await db.execute(
        select(
            ProductAttributeValue.product_id,
            Attribute.code,
            ProductAttributeValue.value_number,
            ProductAttributeValue.value_text,
            ProductAttributeValue.value_bool,
        )
        .join(Attribute, ProductAttributeValue.attribute_id == Attribute.id)
        .where(ProductAttributeValue.product_id.in_(product_ids))
    )
    values: dict[int, dict[str, Any]] = {}
    for product_id, code, value_number, value_text, value_bool in result.all():
        if value_number is not None:
            typed: Any = float(value_number)
        elif value_bool is not None:
            typed = bool(value_bool)
        elif value_text is not None:
            typed = value_text
        else:
            continue
        values.setdefault(product_id, {})[code] = typed
    return values


async def _load_brand_values(
    db: AsyncSession, product_ids: list[int]
) -> dict[int, str]:
    """Brand attribute values (``value_text`` of attribute named «Бренд»).

    Separate from ``_load_attribute_values``: the brand is matched by NAME
    (in real 1C data the attribute code is a GUID), the same resolution as
    the product detail endpoint.
    """
    if not product_ids:
        return {}
    result = await db.execute(
        select(ProductAttributeValue.product_id, ProductAttributeValue.value_text)
        .join(Attribute, ProductAttributeValue.attribute_id == Attribute.id)
        .where(
            ProductAttributeValue.product_id.in_(product_ids),
            Attribute.name == BRAND_ATTRIBUTE_NAME,
            ProductAttributeValue.value_text.isnot(None),
        )
    )
    return {
        product_id: brand
        for product_id, value_text in result.all()
        if (brand := normalize_brand_value(value_text)) is not None
    }


def _product_document(
    product: Product,
    category_paths: dict[int, tuple[Category, Category | None]],
    attr_values: dict[str, Any],
    brand: str | None = None,
) -> dict[str, Any]:
    """Build one Meilisearch document (stable field names, D-11)."""
    categories: dict[str, str] = {}
    if product.category_id is not None and product.category_id in category_paths:
        category, parent = category_paths[product.category_id]
        if parent is not None:
            categories["lvl0"] = parent.name
            categories["lvl1"] = f"{parent.name} > {category.name}"
        else:
            categories["lvl0"] = category.name
    return {
        "id": product.id,
        "onec_id": product.onec_id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "price": float(product.price) if product.price is not None else None,
        "stock": product.stock or 0,
        "category_id": product.category_id,
        "categories": categories,
        "attrs": attr_values,
        "images": product.images or [],
        # Card fields (pixel-perfect-homepage): brand is stable (changes only
        # via product writes / 1C intake), created_at is immutable — the API
        # derives ``is_new`` from it at query time, so it never goes stale.
        # Volatile aggregates (rating/reviews/is_hit) are NOT indexed: reviews
        # and paid orders don't touch the products row, so partial updates
        # would miss them — they are enriched from the DB at query time.
        "brand": brand,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }


async def build_product_documents(
    db: AsyncSession, product_ids: Iterable[int]
) -> tuple[list[dict[str, Any]], list[int]]:
    """Build documents for the given products.

    Returns ``(documents, deleted_ids)``: soft-deleted (``is_active=False``)
    and missing product ids go to ``deleted_ids`` so the caller removes them
    from the index (D-06).
    """
    ids = sorted({int(pid) for pid in product_ids})
    if not ids:
        return [], []
    result = await db.execute(select(Product).where(Product.id.in_(ids)))
    products = result.scalars().all()
    by_id = {p.id: p for p in products}

    active = [p for p in products if p.is_active]
    deleted_ids = [pid for pid in ids if pid not in by_id or not by_id[pid].is_active]

    category_paths = await _load_category_paths(db, [p.category_id for p in active])
    attr_values = await _load_attribute_values(db, [p.id for p in active])
    brand_values = await _load_brand_values(db, [p.id for p in active])

    documents = [
        _product_document(
            p, category_paths, attr_values.get(p.id, {}), brand_values.get(p.id)
        )
        for p in active
    ]
    return documents, deleted_ids


def index_products_partial(
    client: meilisearch.Client,
    documents: list[dict[str, Any]],
    index_uid: str = PRODUCTS_INDEX,
    batch_size: int = PARTIAL_BATCH_SIZE,
) -> int:
    """Partial update (add-or-replace) in batches of ~1000 docs (D-06).

    Each batch task is awaited so indexing errors surface early and the
    calling job can be retried by the worker.
    """
    indexed = 0
    index = client.index(index_uid)
    for offset in range(0, len(documents), batch_size):
        batch = documents[offset : offset + batch_size]
        task = index.add_documents(batch)
        wait_for_task(client, task.task_uid)
        indexed += len(batch)
    return indexed


def delete_products(
    client: meilisearch.Client,
    product_ids: Iterable[int],
    index_uid: str = PRODUCTS_INDEX,
) -> int:
    """Delete documents (soft-deleted / removed products) via delete-batch."""
    ids = sorted({int(pid) for pid in product_ids})
    if not ids:
        return 0
    task = client.index(index_uid).delete_documents(ids)
    wait_for_task(client, task.task_uid)
    return len(ids)


async def find_products_updated_since(db: AsyncSession, since: datetime) -> list[int]:
    """Ids of products whose row changed at or after ``since`` (watermark).

    Compensation for partial updates lost during a swap-reindex (review F004):
    every write path (1C webhook/intake apply, admin edits) updates the
    ``products`` row, and ``updated_at`` has an ``onupdate`` trigger, so this
    watermark catches exactly the products whose partial update may have
    landed in the pre-swap index. Inactive products are included — the
    partial handler routes them to delete-batch.
    """
    result = await db.execute(
        select(Product.id).where(Product.updated_at >= since).order_by(Product.id)
    )
    return [row[0] for row in result.all()]


async def reindex_full(
    db: AsyncSession,
    client: meilisearch.Client,
    batch_size: int = REINDEX_BATCH_SIZE,
) -> dict[str, int]:
    """Zero-downtime full reindex via swap indexes (D-06).

    Flow: ensure the serving index exists (settings NOT touched — D-06) →
    provision settings in ``products_new`` (BEFORE any documents) → load all
    active products in batches → ``POST /swap-indexes`` (atomic) → delete the
    old index content (``products_new`` after the swap). A failed task raises
    and aborts the flow BEFORE the swap, so the serving index is never touched
    by a broken build; the job worker retries the job.

    All sync Meilisearch SDK calls run via ``asyncio.to_thread`` so the job
    worker event loop (shared with CDEK/payments/intake jobs) is never
    blocked for the duration of a reindex (review F001).
    """
    filterable_codes = await get_filterable_attr_codes(db)

    # Ensure both indexes exist before swap (swap fails on a missing index).
    # Settings are applied ONLY to products_new BEFORE documents — never
    # "live" on the serving index (review F002, spec Risks).
    await asyncio.to_thread(ensure_index_exists, client, PRODUCTS_INDEX)
    await asyncio.to_thread(provision_index, client, PRODUCTS_INDEX_NEW, filterable_codes)

    indexed = 0
    last_id = 0
    while True:
        result = await db.execute(
            select(Product.id)
            .where(Product.is_active.is_(True), Product.id > last_id)
            .order_by(Product.id)
            .limit(batch_size)
        )
        batch_ids = [row[0] for row in result.all()]
        if not batch_ids:
            break
        documents, _ = await build_product_documents(db, batch_ids)
        indexed += await _to_thread_index(client, documents, PRODUCTS_INDEX_NEW)
        last_id = batch_ids[-1]

    # Atomic swap: serving index keeps working during the whole build (D-06).
    swap_task = await asyncio.to_thread(
        client.swap_indexes, [{"indexes": [PRODUCTS_INDEX, PRODUCTS_INDEX_NEW]}]
    )
    await asyncio.to_thread(wait_for_task, client, swap_task.task_uid)

    # After the swap, ``products_new`` holds the OLD index — drop it.
    delete_task = await asyncio.to_thread(client.delete_index, PRODUCTS_INDEX_NEW)
    await asyncio.to_thread(wait_for_task, client, delete_task.task_uid)

    return {"indexed": indexed}


async def _to_thread_index(
    client: meilisearch.Client,
    documents: list[dict[str, Any]],
    index_uid: str,
) -> int:
    """Run the sync partial-index helper without blocking the event loop."""
    return await asyncio.to_thread(index_products_partial, client, documents, index_uid)
