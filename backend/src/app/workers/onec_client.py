import logging
import os
import re
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

import aiohttp

from src.app.core.config import settings
from src.app.schemas.onec import (
    OnecCategoryOdata,
    OnecPriceOdata,
    OnecProductOdata,
    OnecStockOdata,
)

logger = logging.getLogger(__name__)

_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class OnecClientError(Exception):
    """Base exception for 1C OData client errors."""


class OnecClientAuthError(OnecClientError):
    """Raised when 1C rejects authentication."""


class OnecClientConfigurationError(OnecClientError):
    """Raised when client is misconfigured (URL, GUID, etc.)."""


def _is_valid_guid(value: str) -> bool:
    return bool(_GUID_RE.match(value))


def _escape_odata_string(value: str) -> str:
    """Escape single quotes for OData string literals."""
    return value.replace("'", "''")


def _validate_base_url(url: str) -> str:
    """Validate ``url`` against SSRF / unsafe endpoints in production.

    Mirrors the fail-fast pattern from ``_load_secret_key`` and
    ``_validate_frontend_url``. Dev/test are unrestricted.
    """
    import ipaddress
    from urllib.parse import urlparse

    if not url:
        raise OnecClientConfigurationError("ONEC_API_URL is not configured")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        raise OnecClientConfigurationError(f"ONEC_API_URL is not a valid URL: {url!r}")

    if os.getenv("ENVIRONMENT") == "production":
        if parsed.scheme != "https":
            raise OnecClientConfigurationError(
                f"ONEC_API_URL must use https:// in production. Got: {url!r}"
            )
        host = parsed.hostname
        if host in ("localhost",):
            raise OnecClientConfigurationError(
                f"ONEC_API_URL must not point at localhost in production. Got: {url!r}"
            )
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified:
                raise OnecClientConfigurationError(
                    f"ONEC_API_URL must not point at a loopback/private/link-local IP "
                    f"in production. Got: {url!r}"
                )
        except ValueError:
            # Not an IP literal — a real domain name, which is fine.
            pass

    return url.rstrip("/")


class OnecClient:
    """Async OData client for 1C:УНФ.

    Uses ``aiohttp`` with HTTP Basic Auth. All methods support pagination
    through ``$top``/``$skip`` query options and return parsed Pydantic
    schemas from ``src.app.schemas.onec``.
    """

    def __init__(
        self,
        base_url: str | None = None,
        login: str | None = None,
        password: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = _validate_base_url(base_url or settings.onec_api_url or "")
        self.login = login or settings.onec_login or ""
        self.password = password or settings.onec_password or ""
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    def _session_or_create(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            auth = None
            if self.login and self.password:
                auth = aiohttp.BasicAuth(self.login, self.password)
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                auth=auth,
                headers={"Accept": "application/json"},
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "OnecClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        session = self._session_or_create()
        try:
            async with session.request(method, url, params=params or {}) as response:
                if response.status == 401:
                    raise OnecClientAuthError("Invalid 1C credentials")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as exc:
            logger.warning("1C API request failed: %s %s -> %s", method, url, exc.status)
            raise OnecClientError(f"1C API request failed: {exc.status}") from exc
        except aiohttp.ClientError as exc:
            logger.warning("1C API request failed: %s %s -> %s", method, url, exc)
            raise OnecClientError(f"1C API request failed: {exc}") from exc

    @staticmethod
    def _normalize_guid(value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        # OData sometimes returns empty GUIDs as a zero-filled string.
        if value == "00000000-0000-0000-0000-000000000000":
            return None
        return value

    # ─── Categories ───────────────────────────────────────────────────────────

    async def get_categories(
        self,
        top: int = 100,
        skip: int = 0,
    ) -> list[OnecCategoryOdata]:
        """Fetch product categories from Catalog_КатегорииНоменклатуры."""
        data = await self._request(
            "GET",
            "/Catalog_КатегорииНоменклатуры",
            params={"$top": top, "$skip": skip, "$format": "json"},
        )
        result: list[OnecCategoryOdata] = []
        for item in data.get("value", []) if isinstance(data, dict) else []:
            ref_key = self._normalize_guid(item.get("Ref_Key"))
            if not ref_key:
                logger.warning("Skipping 1C category with empty Ref_Key")
                continue
            result.append(
                OnecCategoryOdata(
                    ref_key=ref_key,
                    parent_key=self._normalize_guid(item.get("Parent_Key")),
                    description=item.get("Description") or "",
                )
            )
        return result

    async def get_all_categories(self) -> list[OnecCategoryOdata]:
        """Fetch all categories across pages."""
        return await self._fetch_all(self.get_categories)

    # ─── Products ─────────────────────────────────────────────────────────────

    async def get_products(
        self,
        top: int = 100,
        skip: int = 0,
    ) -> list[OnecProductOdata]:
        """Fetch real stock products from Catalog_Номенклатуры.

        Filters out groups and non-stock items.
        """
        filter_expr = "ТипНоменклатуры eq 'Запас' and IsFolder eq false"
        data = await self._request(
            "GET",
            "/Catalog_Номенклатура",
            params={
                "$top": top,
                "$skip": skip,
                "$filter": filter_expr,
                "$format": "json",
            },
        )
        result: list[OnecProductOdata] = []
        for item in data.get("value", []) if isinstance(data, dict) else []:
            ref_key = self._normalize_guid(item.get("Ref_Key"))
            if not ref_key:
                logger.warning("Skipping 1C product with empty Ref_Key")
                continue
            result.append(
                OnecProductOdata(
                    ref_key=ref_key,
                    description=item.get("Description") or "",
                    article=item.get("Артикул") or None,
                    code=item.get("Code") or None,
                    parent_key=self._normalize_guid(item.get("Parent_Key")),
                    is_folder=bool(item.get("IsFolder", False)),
                    item_type=item.get("ТипНоменклатуры") or "",
                )
            )
        return result

    async def get_all_products(self) -> list[OnecProductOdata]:
        """Fetch all products across pages."""
        return await self._fetch_all(self.get_products)

    # ─── Prices ───────────────────────────────────────────────────────────────

    async def get_prices(
        self,
        price_type_key: str | None = None,
        top: int = 100,
        skip: int = 0,
    ) -> list[OnecPriceOdata]:
        """Fetch prices from InformationRegister_ЦеныНоменклатуры.

        Без ``price_type_key`` запрос идёт без ``$filter`` — тянем все виды
        цен (D-04). GUID-валидация — только для явно переданного параметра.
        """
        params: dict[str, Any] = {"$top": top, "$skip": skip, "$format": "json"}
        if price_type_key:
            price_type = price_type_key.strip()
            if not _is_valid_guid(price_type):
                raise OnecClientConfigurationError(
                    f"price_type_key must be a valid GUID. Got: {price_type!r}"
                )
            params["$filter"] = f"ВидЦен_Key eq '{_escape_odata_string(price_type)}'"
        data = await self._request(
            "GET",
            "/InformationRegister_ЦеныНоменклатуры",
            params=params,
        )
        result: list[OnecPriceOdata] = []
        for item in data.get("value", []) if isinstance(data, dict) else []:
            product_key = self._normalize_guid(item.get("Номенклатура_Key"))
            if not product_key:
                logger.warning("Skipping 1C price with empty product Ref_Key")
                continue
            result.append(
                OnecPriceOdata(
                    product_key=product_key,
                    price_type_key=self._normalize_guid(item.get("ВидЦен_Key")),
                    price=Decimal(str(item.get("Цена", 0) or 0)),
                )
            )
        return result

    async def get_all_prices(self, price_type_key: str | None = None) -> list[OnecPriceOdata]:
        """Fetch all prices across pages."""

        async def _page(top: int, skip: int) -> list[OnecPriceOdata]:
            return await self.get_prices(price_type_key, top=top, skip=skip)

        return await self._fetch_all(_page)

    # ─── Stock balances ───────────────────────────────────────────────────────

    async def get_stock_balance(
        self,
        warehouse_key: str | None = None,
        top: int = 100,
        skip: int = 0,
    ) -> list[OnecStockOdata]:
        """Fetch stock balances from AccumulationRegister_ЗапасыНаСкладах/Balance.

        If ``warehouse_key`` is not provided, balances are aggregated by product
        across all warehouses.
        """
        warehouse = warehouse_key or settings.onec_warehouse_key
        params: dict[str, Any] = {"$top": top, "$skip": skip, "$format": "json"}
        if warehouse:
            warehouse = warehouse.strip()
            if not _is_valid_guid(warehouse):
                raise OnecClientConfigurationError(
                    f"ONEC_WAREHOUSE_KEY must be a valid GUID. Got: {warehouse!r}"
                )
            params["$filter"] = f"Склад_Key eq '{_escape_odata_string(warehouse)}'"

        data = await self._request(
            "GET",
            "/AccumulationRegister_ЗапасыНаСкладах/Balance",
            params=params,
        )

        raw_balances: dict[str, dict[str, Any]] = {}
        for item in data.get("value", []) if isinstance(data, dict) else []:
            product_key = self._normalize_guid(item.get("Номенклатура_Key"))
            if not product_key:
                logger.warning("Skipping 1C stock balance with empty product Ref_Key")
                continue
            wh_key = self._normalize_guid(item.get("Склад_Key"))
            qty_key = "КоличествоBalance" if "КоличествоBalance" in item else "Количество"
            quantity = round(item.get(qty_key, 0) or 0)
            if product_key not in raw_balances:
                raw_balances[product_key] = {"quantity": 0, "warehouse_key": wh_key}
            raw_balances[product_key]["quantity"] += quantity
            # When summing across warehouses we drop the per-row warehouse key.
            if not warehouse:
                raw_balances[product_key]["warehouse_key"] = None

        result: list[OnecStockOdata] = []
        for product_key, agg in raw_balances.items():
            result.append(
                OnecStockOdata(
                    product_key=product_key,
                    warehouse_key=agg["warehouse_key"],
                    quantity=agg["quantity"],
                )
            )
        return result

    async def get_all_stock_balance(
        self, warehouse_key: str | None = None
    ) -> list[OnecStockOdata]:
        """Fetch all stock balances across pages."""

        async def _page(top: int, skip: int) -> list[OnecStockOdata]:
            return await self.get_stock_balance(warehouse_key, top=top, skip=skip)

        return await self._fetch_all(_page)

    # ─── Pagination helper ────────────────────────────────────────────────────

    async def _fetch_all(
        self,
        fetch_page: Callable[[int, int], Awaitable[list[Any]]],
        page_size: int = 100,
    ) -> list[Any]:
        """Fetch all pages using $top/$skip until a page returns fewer rows."""
        all_items: list[Any] = []
        skip = 0
        while True:
            page = await fetch_page(top=page_size, skip=skip)
            if not page:
                break
            all_items.extend(page)
            if len(page) < page_size:
                break
            skip += page_size
        return all_items
