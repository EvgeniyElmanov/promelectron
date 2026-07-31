"""Catalog search query building and facet merging (Phase 5, issue #121).

Decisions: D-03 (backend proxy — keys never leave the server), D-08
(disjunctive facets via multi-search: one main query + one ``limit: 0``
subquery per ACTIVE facet group with that group's filter excluded),
D-11 (stable document field names).

Security (PLAN R4): attribute codes are validated against the ``attributes``
catalog (whitelist), numbers are typed, strings are quote-escaped — raw user
input is never interpolated into a filter expression.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from meilisearch.errors import MeilisearchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.attribute import Attribute, AttributeValueType
from src.app.models.category import Category
from src.app.services.search_service import (
    PRODUCTS_INDEX,
    SearchUnavailableError,
    facet_search_async,
    get_meili_client,
    multi_search_async,
    search_async,
)

logger = logging.getLogger(__name__)

SEARCH_CACHE_TTL_SECONDS = 60

SORT_MAP: dict[str, list[str]] = {
    "price_asc": ["price:asc"],
    "price_desc": ["price:desc"],
    "name_asc": ["name:asc"],
    "newest": ["id:desc"],
}

BASE_FACETS = ["price", "categories.lvl0", "categories.lvl1"]
BASE_FACET_META: list[dict[str, Any]] = [
    {"code": "categories.lvl0", "name": "Категория", "value_type": "string", "unit": None},
    {"code": "categories.lvl1", "name": "Подкатегория", "value_type": "string", "unit": None},
    {"code": "price", "name": "Цена", "value_type": "number", "unit": None},
]


class SearchQueryError(ValueError):
    """Invalid search query parameters (mapped to HTTP 400)."""


def escape_filter_string(value: str) -> str:
    """Escape a string literal for a Meilisearch filter expression."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _format_filter_value(value: str, value_type: AttributeValueType) -> Any:
    """Cast a raw query value to its typed filter literal (D-10)."""
    if value_type == AttributeValueType.number:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise SearchQueryError(f"Expected numeric value, got {value!r}") from None
    if value_type == AttributeValueType.bool:
        lowered = value.strip().lower()
        if lowered in ("true", "1"):
            return True
        if lowered in ("false", "0"):
            return False
        raise SearchQueryError(f"Expected boolean value, got {value!r}")
    return value


def _literal(value: Any) -> str:
    """Render a typed value as a Meilisearch filter literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return f"'{escape_filter_string(str(value))}'"


async def load_filterable_attributes(db: AsyncSession) -> list[Attribute]:
    """Filterable attributes with metadata (whitelist for codes, PLAN R4)."""
    result = await db.execute(
        select(Attribute)
        .where(Attribute.is_filterable.is_(True))
        .order_by(Attribute.sort, Attribute.code)
    )
    return list(result.scalars().all())


def parse_attr_query_params(
    query_params: Any,
    attributes_by_code: dict[str, Attribute],
) -> tuple[dict[str, list[Any]], dict[str, tuple[float, float]]]:
    """Parse repeating ``attr.<code>`` / ``attrs_range.<code>=min:max`` params.

    Returns ``(attr_groups, range_filters)`` with typed values. Unknown or
    non-filterable codes and malformed values raise ``SearchQueryError``.
    """
    attr_groups: dict[str, list[Any]] = {}
    range_filters: dict[str, tuple[float, float]] = {}
    for key, raw in query_params.multi_items():
        if key.startswith("attrs_range."):
            code = key[len("attrs_range.") :]
            attribute = attributes_by_code.get(code)
            if attribute is None:
                raise SearchQueryError(f"Unknown or non-filterable attribute: {code}")
            if attribute.value_type != AttributeValueType.number:
                raise SearchQueryError(f"Range filter requires a numeric attribute: {code}")
            parts = raw.split(":")
            if len(parts) != 2:
                raise SearchQueryError(
                    f"Range filter must be '<min>:<max>', got {raw!r}"
                )
            try:
                range_filters[code] = (float(parts[0]), float(parts[1]))
            except ValueError:
                raise SearchQueryError(
                    f"Range bounds must be numeric, got {raw!r}"
                ) from None
        elif key.startswith("attr."):
            code = key[len("attr.") :]
            attribute = attributes_by_code.get(code)
            if attribute is None:
                raise SearchQueryError(f"Unknown or non-filterable attribute: {code}")
            attr_groups.setdefault(code, []).append(
                _format_filter_value(raw, attribute.value_type)
            )
    return attr_groups, range_filters


async def build_category_filter(db: AsyncSession, category_id: int) -> str:
    """Hierarchical category filter from the denormalized path (D-07).

    Root category → ``categories.lvl0 = '<name>'``; second level →
    ``categories.lvl1 = '<root> > <child>'`` (exact path match covers the
    two catalog levels; lvl2 is only a reserve).
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalars().first()
    if category is None:
        raise SearchQueryError(f"Category not found: {category_id}")
    if category.parent_id is None:
        return f"categories.lvl0 = {_literal(category.name)}"
    result = await db.execute(select(Category).where(Category.id == category.parent_id))
    parent = result.scalars().first()
    path = f"{parent.name} > {category.name}" if parent else category.name
    return f"categories.lvl1 = {_literal(path)}"


def build_filter_expression(
    category_expr: str | None,
    price_min: float | None,
    price_max: float | None,
    attr_groups: dict[str, list[Any]],
    range_filters: dict[str, tuple[float, float]],
) -> list[Any]:
    """AND-of-OR-groups filter array (D-08: OR inside a group, AND between)."""
    filters: list[Any] = []
    if category_expr:
        filters.append(category_expr)
    if price_min is not None and price_max is not None:
        filters.append(f"price {price_min!r} TO {price_max!r}")
    elif price_min is not None:
        filters.append(f"price >= {price_min!r}")
    elif price_max is not None:
        filters.append(f"price <= {price_max!r}")
    for code in sorted(attr_groups):
        values = ", ".join(_literal(v) for v in attr_groups[code])
        filters.append([f"attrs.{code} IN [{values}]"])
    for code in sorted(range_filters):
        low, high = range_filters[code]
        filters.append(f"attrs.{code} {low!r} TO {high!r}")
    return filters


def _without_group(filters: list[Any], code: str) -> list[Any]:
    """Remove one facet group's filter (for disjunctive subqueries, D-08)."""
    prefix = f"attrs.{code} "
    return [
        f
        for f in filters
        if not (
            (isinstance(f, str) and f.startswith(prefix))
            or (isinstance(f, list) and any(s.startswith(prefix) for s in f))
        )
    ]


def merge_facet_results(
    main_result: dict[str, Any],
    sub_results: list[tuple[str, dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Merge disjunctive subquery facet distributions into the main result.

    ``sub_results`` — ``(attr_code, multi_search_result)`` pairs for active
    groups; the group's distribution is replaced by the subquery's (filter
    of that group excluded), so counts of other values in the group stay
    alive (D-08).
    """
    distribution = dict(main_result.get("facetDistribution") or {})
    stats = dict(main_result.get("facetStats") or {})
    for code, sub in sub_results:
        sub_distribution = sub.get("facetDistribution") or {}
        key = f"attrs.{code}"
        if key in sub_distribution:
            distribution[key] = sub_distribution[key]
        sub_stats = sub.get("facetStats") or {}
        if key in sub_stats:
            stats[key] = sub_stats[key]
    return distribution, stats


def build_facets_response(
    attributes: list[Attribute],
    distribution: dict[str, Any],
    stats: dict[str, Any],
) -> list[dict[str, Any]]:
    """Shape facets for the API contract: values for discrete, stats for numeric."""
    facets: list[dict[str, Any]] = []
    for meta in BASE_FACET_META:
        code = meta["code"]
        entry = dict(meta)
        if meta["value_type"] == "number":
            entry["stats"] = stats.get(code)
        else:
            entry["values"] = [
                {"value": value, "count": count}
                for value, count in (distribution.get(code) or {}).items()
            ]
        facets.append(entry)
    for attribute in attributes:
        key = f"attrs.{attribute.code}"
        entry: dict[str, Any] = {
            "code": attribute.code,
            "name": attribute.name,
            "value_type": attribute.value_type.value,
            "unit": attribute.unit,
        }
        if attribute.value_type == AttributeValueType.number:
            entry["stats"] = stats.get(key)
        else:
            entry["values"] = [
                {"value": value, "count": count}
                for value, count in (distribution.get(key) or {}).items()
            ]
        facets.append(entry)
    return facets


async def search_products(
    db: AsyncSession,
    q: str | None,
    category_id: int | None,
    page: int,
    hits_per_page: int,
    sort: str | None,
    price_min: float | None,
    price_max: float | None,
    query_params: Any,
) -> dict[str, Any]:
    """Run the disjunctive multi-search and shape the API response (D-08)."""
    if sort is not None and sort not in SORT_MAP:
        raise SearchQueryError(
            f"Unknown sort: {sort}. Allowed: {', '.join(sorted(SORT_MAP))}"
        )

    attributes = await load_filterable_attributes(db)
    attributes_by_code = {a.code: a for a in attributes}
    attr_groups, range_filters = parse_attr_query_params(query_params, attributes_by_code)

    category_expr = None
    if category_id is not None:
        category_expr = await build_category_filter(db, category_id)

    filters = build_filter_expression(
        category_expr, price_min, price_max, attr_groups, range_filters
    )
    facet_fields = BASE_FACETS + [f"attrs.{a.code}" for a in attributes]

    queries: list[dict[str, Any]] = [
        {
            "indexUid": PRODUCTS_INDEX,
            "q": q or "",
            "filter": filters,
            "facets": facet_fields,
            "page": page,
            "hitsPerPage": hits_per_page,
            **({"sort": SORT_MAP[sort]} if sort else {}),
        }
    ]
    active_groups = sorted(set(attr_groups) | set(range_filters))
    for code in active_groups:
        queries.append(
            {
                "indexUid": PRODUCTS_INDEX,
                "q": q or "",
                "filter": _without_group(filters, code),
                "facets": [f"attrs.{code}"],
                "limit": 0,
            }
        )

    try:
        client = get_meili_client()
        result = await multi_search_async(client, queries)
    except SearchUnavailableError:
        raise
    except MeilisearchError as exc:
        raise SearchUnavailableError(f"Meilisearch request failed: {exc}") from exc

    results = result.get("results") or []
    main = results[0] if results else {}
    sub_results = [
        (code, results[i + 1]) for i, code in enumerate(active_groups) if i + 1 < len(results)
    ]
    distribution, stats = merge_facet_results(main, sub_results)

    total = main.get("totalHits", 0)
    return {
        "items": main.get("hits", []),
        "total": total,
        "page": page,
        "pages": main.get("totalPages", 0),
        "facets": build_facets_response(attributes, distribution, stats),
    }


async def search_suggestions(
    q: str | None, limit: int
) -> dict[str, Any]:
    """Quick product suggestions for the search box (frontend contract)."""
    try:
        client = get_meili_client()
        result = await search_async(
            client,
            PRODUCTS_INDEX,
            q or "",
            {
                "limit": limit,
                "attributesToRetrieve": ["id", "name", "sku"],
                "attributesToHighlight": ["name"],
            },
        )
    except SearchUnavailableError:
        raise
    except MeilisearchError as exc:
        raise SearchUnavailableError(f"Meilisearch request failed: {exc}") from exc
    return {
        "suggestions": [
            {"type": "product", "id": hit.get("id"), "name": hit.get("name")}
            for hit in result.get("hits", [])
        ]
    }


async def search_facet_values(
    db: AsyncSession, facet: str, q: str | None
) -> dict[str, Any]:
    """Proxy to the Meilisearch facet-search API for long enum facets.

    Only discrete (enum/string) filterable attributes are allowed — facet
    search does not work for numbers (rejected with HTTP 400).
    """
    attributes = await load_filterable_attributes(db)
    attribute = next((a for a in attributes if a.code == facet), None)
    if attribute is None:
        raise SearchQueryError(f"Unknown or non-filterable facet: {facet}")
    if attribute.value_type == AttributeValueType.number:
        raise SearchQueryError("Facet search is not supported for numeric facets")
    try:
        client = get_meili_client()
        result = await facet_search_async(
            client, PRODUCTS_INDEX, f"attrs.{attribute.code}", q
        )
    except SearchUnavailableError:
        raise
    except MeilisearchError as exc:
        raise SearchUnavailableError(f"Meilisearch request failed: {exc}") from exc
    return {
        "values": [
            {"value": hit.get("value"), "count": hit.get("count")}
            for hit in result.get("facetHits", [])
        ]
    }


def map_search_errors(exc: Exception) -> HTTPException:
    """Translate service-layer errors to HTTP responses."""
    if isinstance(exc, SearchQueryError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=503, detail="Search service unavailable")
