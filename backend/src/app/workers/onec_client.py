import logging
from dataclasses import dataclass
from typing import Any

import requests

from src.app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OnecProduct:
    sku: str
    name: str
    description: str | None
    price: float
    stock: int
    category_name: str | None
    weight_grams: int = 1000
    length_cm: int | None = None
    width_cm: int | None = None
    height_cm: int | None = None
    is_active: bool = True


class OnecClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.onec_api_url or "").rstrip("/")
        self.api_key = api_key or settings.onec_api_key or ""
        self.timeout = 30

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            logger.warning("1C API request failed: %s", exc)
            raise

    def get_products(self) -> list[OnecProduct]:
        """Fetch products from 1C ERP.

        Expected response format (JSON):
        [
            {
                "sku": "1C-001",
                "name": "Product Name",
                "description": "...",
                "price": 1000.0,
                "stock": 10,
                "category_name": "Category",
                "is_active": true
            }
        ]
        """
        if not self.base_url:
            logger.info("ONEC_API_URL not configured — returning empty product list")
            return []

        try:
            resp = self._request("GET", "/products")
            data = resp.json()
        except Exception:
            logger.exception("Failed to fetch products from 1C")
            return []

        products: list[OnecProduct] = []
        for item in data if isinstance(data, list) else []:
            try:
                products.append(
                    OnecProduct(
                        sku=str(item.get("sku", "")),
                        name=str(item.get("name", "")),
                        description=item.get("description"),
                        price=float(item.get("price", 0)),
                        stock=int(item.get("stock", 0)),
                        category_name=item.get("category_name"),
                        weight_grams=int(item.get("weight_grams", 1000)),
                        length_cm=item.get("length_cm"),
                        width_cm=item.get("width_cm"),
                        height_cm=item.get("height_cm"),
                        is_active=bool(item.get("is_active", True)),
                    )
                )
            except (TypeError, ValueError) as exc:
                logger.warning("Skipping malformed 1C product: %s — %s", item, exc)
                continue

        logger.info("Fetched %s products from 1C", len(products))
        return products
