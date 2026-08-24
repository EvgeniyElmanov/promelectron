"""Response schemas for the public catalog search API (issue #121, F003).

Stable public contract: the endpoint returns product cards shaped from the
Meilisearch document — never the raw document (``description``, ``onec_id``
and other internal fields stay on the server).
"""

from typing import Any

from pydantic import BaseModel


class SearchItemOut(BaseModel):
    """Product card as returned by ``GET /api/v1/search/``."""

    id: int
    sku: str | None = None
    name: str
    price: float | None = None
    stock: int = 0
    category_id: int | None = None
    categories: dict[str, str] = {}
    attrs: dict[str, Any] = {}
    images: list[str] = []


class SuggestionProduct(BaseModel):
    """One product suggestion (``image`` — primary photo or ``None``, D-05)."""

    id: int
    name: str
    price: float | None = None
    image: str | None = None


class SuggestionsResponse(BaseModel):
    """Contract of ``GET /api/v1/search/suggestions/`` (issue #138).

    ``queries``/``categories``/``brands`` are empty until real data sources
    exist for them (D-04); ``products`` carries top-N hits with price/image.
    """

    queries: list[str] = []
    categories: list = []
    brands: list[str] = []
    products: list[SuggestionProduct] = []


class FacetValueOut(BaseModel):
    value: Any
    count: int


class FacetStatsOut(BaseModel):
    min: float
    max: float


class FacetOut(BaseModel):
    code: str
    name: str
    value_type: str
    unit: str | None = None
    values: list[FacetValueOut] | None = None
    stats: FacetStatsOut | None = None


class SearchResponse(BaseModel):
    items: list[SearchItemOut]
    total: int
    page: int
    pages: int
    facets: list[FacetOut]
