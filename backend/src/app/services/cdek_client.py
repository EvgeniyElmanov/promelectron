import json
import logging
from typing import Any

import httpx

from src.app.core.config import settings
from src.app.core.redis_client import RedisClient

logger = logging.getLogger(__name__)

TOKEN_CACHE_KEY = "cdek:access_token"


class CdekAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class CdekClient:
    def __init__(self, base_url: str | None = None, account: str | None = None, secure: str | None = None):
        self.base_url = (base_url or settings.cdek_api_url).rstrip("/")
        self.account = account or settings.cdek_account
        self.secure = secure or settings.cdek_secure
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self) -> None:
        await self._http.aclose()

    def _test_mode_fallback(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Return deterministic mock responses when CDEK_TEST_MODE is enabled
        and credentials are not configured. Useful for local E2E/frontend tests.
        """
        if not settings.cdek_test_mode or (self.account and self.secure):
            return None

        logger.warning(
            "CDEK_TEST_MODE=true but CDEK_ACCOUNT/CDEK_SECURE are not set; "
            "using deterministic mock responses"
        )

        if path == "/v2/oauth/token":
            return {"access_token": "test-token", "expires_in": 3600}

        if path == "/v2/location/suggest/cities":
            name = (params or {}).get("name", "")
            return [
                {"code": 44, "city": f"{name} (тест)", "country_code": "RU"},
            ]

        if path == "/v2/deliverypoints":
            return [
                {
                    "code": "TEST_PVZ_1",
                    "name": "Тестовый ПВЗ на Тверской",
                    "type": "PVZ",
                    "have_cashless": True,
                    "have_cash": True,
                    "allowed_cod": True,
                    "is_dressing_room": True,
                    "work_time": "Пн-Пт: 10:00-20:00",
                    "dimensions": [{"depth": 50, "width": 50, "height": 50}],
                    "weight_min": 0,
                    "weight_max": 30000,
                    "location": {
                        "city_code": 44,
                        "city": "Москва",
                        "region": "Москва",
                        "country_code": "RU",
                        "postal_code": "101000",
                        "address": "г. Москва, ул. Тверская, д. 1",
                        "latitude": 55.755864,
                        "longitude": 37.617698,
                    },
                },
                {
                    "code": "TEST_PVZ_2",
                    "name": "Тестовый ПВЗ на Арбате",
                    "type": "PVZ",
                    "have_cashless": True,
                    "have_cash": True,
                    "allowed_cod": True,
                    "is_dressing_room": True,
                    "work_time": "Пн-Вс: 09:00-21:00",
                    "dimensions": [{"depth": 60, "width": 60, "height": 60}],
                    "weight_min": 0,
                    "weight_max": 30000,
                    "location": {
                        "city_code": 44,
                        "city": "Москва",
                        "region": "Москва",
                        "country_code": "RU",
                        "postal_code": "119002",
                        "address": "г. Москва, ул. Арбат, д. 10",
                        "latitude": 55.751244,
                        "longitude": 37.60038,
                    },
                },
                {
                    "code": "TEST_PVZ_3",
                    "name": "Тестовый ПВЗ на Красной площади",
                    "type": "PVZ",
                    "have_cashless": False,
                    "have_cash": True,
                    "allowed_cod": True,
                    "is_dressing_room": False,
                    "work_time": "Пн-Пт: 08:00-22:00",
                    "dimensions": [{"depth": 40, "width": 40, "height": 40}],
                    "weight_min": 0,
                    "weight_max": 15000,
                    "location": {
                        "city_code": 44,
                        "city": "Москва",
                        "region": "Москва",
                        "country_code": "RU",
                        "postal_code": "109012",
                        "address": "г. Москва, Красная площадь, д. 3",
                        "latitude": 55.753595,
                        "longitude": 37.621031,
                    },
                },
            ]

        if path == "/v2/calculator/tarifflist":
            return {
                "tariff_codes": [
                    {
                        "tariff_code": 136,
                        "tariff_name": "Экспресс-лайт тест",
                        "tariff_description": "Тестовый тариф",
                        "delivery_mode": 4,
                        "delivery_sum": 350.0,
                        "period_min": 2,
                        "period_max": 4,
                    },
                ],
            }

        if path == "/v2/orders":
            return {
                "entity": {"uuid": "test-cdek-uuid"},
                "requests": [{"state": "ACCEPTED"}],
            }

        if path.startswith("/v2/orders/"):
            return {"entity": {"uuid": "test-cdek-uuid"}, "statuses": []}

        return None

    async def _get_token(self) -> str:
        cached = await RedisClient.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

        fallback = self._test_mode_fallback("POST", "/v2/oauth/token")
        if fallback:
            token = fallback["access_token"]
            await RedisClient.set(TOKEN_CACHE_KEY, token, ttl=3000)
            return token

        if not self.account or not self.secure:
            logger.warning(
                "CDEK_TEST_MODE=false but CDEK_ACCOUNT/CDEK_SECURE are not set; "
                "real CDEK requests will fail"
            )
            raise CdekAPIError("CDEK credentials are not configured")

        response = await self._http.post(
            "/v2/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.account,
                "client_secret": self.secure,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise CdekAPIError(
                f"CDEK auth failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 3599)
        await RedisClient.set(TOKEN_CACHE_KEY, token, ttl=expires_in - 60)
        return token

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fallback = self._test_mode_fallback(method, path, json_data, params)
        if fallback is not None:
            return fallback

        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        response = await self._http.request(
            method=method,
            url=path,
            json=json_data,
            params=params,
            headers=headers,
        )

        body = response.text
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body}

        if response.status_code >= 400:
            raise CdekAPIError(
                f"CDEK API error: {response.status_code} {path}",
                status_code=response.status_code,
                response_body=parsed,
            )

        return parsed

    async def calculate_tariffs(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v2/calculator/tarifflist"""
        return await self._request("POST", "/v2/calculator/tarifflist", json_data=payload)

    async def calculate_tariff(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v2/calculator/tariff"""
        return await self._request("POST", "/v2/calculator/tariff", json_data=payload)

    async def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v2/orders"""
        return await self._request("POST", "/v2/orders", json_data=payload)

    async def get_order(self, cdek_uuid: str) -> dict[str, Any]:
        """GET /v2/orders/{uuid}"""
        return await self._request("GET", f"/v2/orders/{cdek_uuid}")

    async def delete_order(self, cdek_uuid: str) -> dict[str, Any]:
        """DELETE /v2/orders/{uuid}.

        CDEK allows deleting orders only while they are in CREATED status.
        The helper returns the parsed response for 200/204 and raises
        CdekAPIError otherwise.
        """
        return await self._request("DELETE", f"/v2/orders/{cdek_uuid}")

    async def get_delivery_points(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """GET /v2/deliverypoints"""
        result = await self._request("GET", "/v2/deliverypoints", params=params or {})
        if isinstance(result, list):
            return result
        return []

    async def get_delivery_point(self, code: str) -> dict[str, Any] | None:
        """GET /v2/deliverypoints?code=<code> and return the first point with location.city_code."""
        points = await self.get_delivery_points(params={"code": code})
        for point in points:
            location = point.get("location") or {}
            if location.get("city_code") is not None:
                return point
        return None

    async def suggest_cities(self, name: str, country_code: str = "RU") -> list[dict[str, Any]]:
        """GET /v2/location/suggest/cities"""
        return await self._request("GET", "/v2/location/suggest/cities", params={"name": name, "country_code": country_code})


async def get_cdek_client() -> CdekClient:
    """FastAPI-style dependency factory."""
    return CdekClient()
