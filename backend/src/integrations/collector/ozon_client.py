from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

import aiohttp
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from collector.config import Settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 15
_WAIT_MIN = 5.0
_WAIT_MAX = 120.0
_WAIT_MULTIPLIER = 2.0

_PRODUCT_LIST_LIMIT = 1000
_PRODUCT_INFO_BATCH_SIZE = 1000
_FBO_LIMIT = 1000
_FBS_LIMIT = 50
_ANALYTICS_LIMIT = 1000
_STOCK_LIMIT = 100
_TRANSACTION_PAGE_SIZE = 1000
_PRICES_LIMIT = 1000
_PRICE_TIMER_BATCH_SIZE = 1000


def _is_retryable_response(exc: BaseException) -> bool:
    if isinstance(exc, OzonAPIError):
        return exc.status in (429, 500, 502, 503, 504) or exc.is_circuit_open
    return False


def _is_retryable(exc: BaseException) -> bool:
    return _is_retryable_response(exc) or isinstance(
        exc, (aiohttp.ClientError, TimeoutError)
    )


def _log_retry(retry_state: Any) -> None:
    logger.warning(
        "Ozon API retry attempt %d after error: %s",
        retry_state.attempt_number,
        retry_state.outcome.exception(),
    )


class OzonAPIError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        self.is_circuit_open = "Circle is open" in message
        super().__init__(f"HTTP {status}: {message}")


class OzonClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ozon_base_url.rstrip("/")
        self._client_id = settings.ozon_client_id
        self._api_key = settings.ozon_token_reader
        self._request_timeout = settings.ozon_request_timeout
        self._session: aiohttp.ClientSession | None = None

    async def open(self) -> None:
        headers = {
            "Client-Id": self._client_id,
            "Api-Key": self._api_key.get_secret_value(),
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(
            total=self._request_timeout,
            connect=10,
        )
        self._session = aiohttp.ClientSession(
            base_url=self._base_url,
            headers=headers,
            timeout=timeout,
        )

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> OzonClient:
        await self.open()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    @property
    def _client(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError(
                "OzonClient is not open — call open() or use as async context manager"
            )
        return self._session

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        @retry(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(_MAX_RETRIES),
            wait=wait_exponential(
                multiplier=_WAIT_MULTIPLIER, min=_WAIT_MIN, max=_WAIT_MAX
            ),
            before_sleep=_log_retry,
            reraise=True,
        )
        async def _do_request() -> Any:
            async with self._client.post(path, json=body) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise OzonAPIError(resp.status, text)
                data: Any = await resp.json(content_type=None)
                # Check for circuit breaker error in 200 response body
                if isinstance(data, dict):
                    error_msg = data.get("message", "")
                    if "Circle is open" in str(error_msg):
                        raise OzonAPIError(200, str(error_msg))
                return data

        return await _do_request()

    # ------------------------------------------------------------------
    # Pagination helpers
    # ------------------------------------------------------------------

    async def _paginate_last_id(
        self,
        path: str,
        body: dict[str, Any],
        result_key: str,
        items_key: str,
        limit: int,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        last_id = ""
        while True:
            page_body = {**body, "last_id": last_id, "limit": limit}
            data = await self._post(path, page_body)
            result = data.get(result_key, {})
            items: list[dict[str, Any]] = result.get(items_key, []) or []
            if not items:
                break
            yield items
            last_id = result.get("last_id", "")
            if not last_id or len(items) < limit:
                break

    async def _paginate_offset(
        self,
        path: str,
        body: dict[str, Any],
        items_key: str,
        limit: int,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        offset = 0
        while True:
            page_body = {**body, "offset": offset, "limit": limit}
            data = await self._post(path, page_body)
            items: list[dict[str, Any]] = data.get(items_key, []) or []
            if not items:
                break
            yield items
            if len(items) < limit:
                break
            offset += len(items)

    async def _paginate_offset_has_next(
        self,
        path: str,
        body: dict[str, Any],
        result_key: str,
        items_key: str,
        limit: int,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        offset = 0
        while True:
            page_body = {**body, "offset": offset, "limit": limit}
            data = await self._post(path, page_body)
            result = data.get(result_key, {})
            items: list[dict[str, Any]] = result.get(items_key, []) or []
            if not items:
                break
            yield items
            has_next: bool = result.get("has_next", False)
            if not has_next:
                break
            offset += len(items)

    async def _paginate_cursor(
        self,
        path: str,
        body: dict[str, Any],
        items_key: str,
        cursor_key: str,
        limit: int,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        cursor = ""
        while True:
            page_body = {**body, "cursor": cursor, "limit": limit}
            data = await self._post(path, page_body)
            items: list[dict[str, Any]] = data.get(items_key, []) or []
            if not items:
                break
            yield items
            cursor = data.get(cursor_key, "")
            if not cursor or len(items) < limit:
                break

    async def _paginate_pages(
        self,
        path: str,
        body: dict[str, Any],
        result_key: str,
        items_key: str,
        page_size: int,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        page = 1
        while True:
            page_body = {**body, "page": page, "page_size": page_size}
            data = await self._post(path, page_body)
            result = data.get(result_key, {})
            items: list[dict[str, Any]] = result.get(items_key, []) or []
            page_count: int = result.get("page_count", 1)
            if not items:
                break
            yield items
            if page >= page_count:
                break
            page += 1

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    async def get_products_list(
        self, visibility: str = "ALL"
    ) -> AsyncIterator[list[dict[str, Any]]]:
        body: dict[str, Any] = {"filter": {"visibility": visibility}}
        return self._paginate_last_id(
            "/v3/product/list",
            body,
            result_key="result",
            items_key="items",
            limit=_PRODUCT_LIST_LIMIT,
        )

    async def get_products_info(
        self, product_ids: list[int]
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for offset in range(0, len(product_ids), _PRODUCT_INFO_BATCH_SIZE):
            batch = product_ids[offset : offset + _PRODUCT_INFO_BATCH_SIZE]
            data = await self._post(
                "/v3/product/info/list", {"product_id": batch}
            )
            items: list[dict[str, Any]] = (
                data.get("items", []) or data.get("result", {}).get("items", []) or []
            )
            results.extend(items)
            logger.debug(
                "Got product info for %d/%d products",
                min(offset + _PRODUCT_INFO_BATCH_SIZE, len(product_ids)),
                len(product_ids),
            )
        return results

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    async def get_fbo_orders(
        self,
        since: str,
        to: str,
        status: str = "",
    ) -> AsyncIterator[list[dict[str, Any]]]:
        body: dict[str, Any] = {
            "filter": {"since": since, "to": to, "status": status},
            "with": {"analytics_data": True, "financial_data": True},
        }
        return self._paginate_offset(
            "/v2/posting/fbo/list",
            body,
            items_key="result",
            limit=_FBO_LIMIT,
        )

    async def get_fbs_orders(
        self,
        since: str,
        to: str,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        body: dict[str, Any] = {
            "filter": {"since": since, "to": to},
            "with": {"analytics_data": True, "financial_data": True},
        }
        return self._paginate_offset_has_next(
            "/v3/posting/fbs/list",
            body,
            result_key="result",
            items_key="postings",
            limit=_FBS_LIMIT,
        )

    # ------------------------------------------------------------------
    # Finance
    # ------------------------------------------------------------------

    async def get_transactions(
        self,
        date_from: str,
        date_to: str,
        transaction_type: str = "all",
    ) -> AsyncIterator[list[dict[str, Any]]]:
        body: dict[str, Any] = {
            "filter": {
                "date": {"from": date_from, "to": date_to},
                "transaction_type": transaction_type,
            }
        }
        return self._paginate_pages(
            "/v3/finance/transaction/list",
            body,
            result_key="result",
            items_key="operations",
            page_size=_TRANSACTION_PAGE_SIZE,
        )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_analytics_data(
        self,
        date_from: str,
        date_to: str,
        metrics: list[str],
        dimension: list[str],
    ) -> AsyncIterator[list[dict[str, Any]]]:
        import asyncio

        body: dict[str, Any] = {
            "date_from": date_from,
            "date_to": date_to,
            "metrics": metrics,
            "dimension": dimension,
            "filters": [],
            "sort": [],
        }
        offset = 0
        first_page = True
        while True:
            # /v1/analytics/data has 1 req/min limit
            if not first_page:
                logger.info("Waiting 65s for analytics rate limit (1 req/min)")
                await asyncio.sleep(65)
            first_page = False
            page_body = {**body, "offset": offset, "limit": _ANALYTICS_LIMIT}
            data = await self._post("/v1/analytics/data", page_body)
            items: list[dict[str, Any]] = (
                data.get("result", {}).get("data", []) or []
            )
            if not items:
                break
            yield items
            if len(items) < _ANALYTICS_LIMIT:
                break
            offset += len(items)

    async def get_product_queries(
        self,
        skus: list[str],
        date_from: str,
        page: int = 0,
        page_size: int = 1000,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        # Response: {"items": [...], "analytics_period": {...}, "total": N, "page_count": N}
        # Pagination: page/page_count
        body: dict[str, Any] = {
            "date_from": date_from,
            "skus": skus,
            "sort_by": "BY_SEARCHES",
            "sort_dir": "DESCENDING",
        }
        current_page = page
        while True:
            page_body = {**body, "page": current_page, "page_size": page_size}
            data = await self._post("/v1/analytics/product-queries", page_body)
            items: list[dict[str, Any]] = data.get("items", []) or []
            page_count: int = data.get("page_count", 1)
            if not items:
                break
            yield items
            if current_page >= page_count - 1:
                break
            current_page += 1

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------

    async def get_stock_on_warehouses(
        self, warehouse_type: str = "ALL"
    ) -> AsyncIterator[list[dict[str, Any]]]:
        body: dict[str, Any] = {"warehouse_type": warehouse_type}
        offset = 0
        while True:
            page_body = {**body, "offset": offset, "limit": _STOCK_LIMIT}
            data = await self._post("/v2/analytics/stock_on_warehouses", page_body)
            rows: list[dict[str, Any]] = data.get("result", {}).get("rows", []) or []
            if not rows:
                break
            yield rows
            if len(rows) < _STOCK_LIMIT:
                break
            offset += len(rows)

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    async def get_category_tree(self, language: str = "RU") -> dict[str, Any]:
        return await self._post(
            "/v1/description-category/tree", {"language": language}
        )

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------

    async def get_prices(
        self, visibility: str = "ALL"
    ) -> AsyncIterator[list[dict[str, Any]]]:
        body: dict[str, Any] = {"filter": {"visibility": visibility}}
        return self._paginate_cursor(
            "/v5/product/info/prices",
            body,
            items_key="items",
            cursor_key="cursor",
            limit=_PRICES_LIMIT,
        )

    # ------------------------------------------------------------------
    # Price timer
    # ------------------------------------------------------------------

    async def update_price_timer(self, product_ids: list[int]) -> None:
        for offset in range(0, len(product_ids), _PRICE_TIMER_BATCH_SIZE):
            batch = product_ids[offset : offset + _PRICE_TIMER_BATCH_SIZE]
            await self._post(
                "/v1/product/action/timer/update",
                {"product_ids": [str(pid) for pid in batch]},
            )
            logger.info(
                "Price timer updated for %d/%d products",
                min(offset + _PRICE_TIMER_BATCH_SIZE, len(product_ids)),
                len(product_ids),
            )
