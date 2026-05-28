import pytest
from unittest.mock import patch

from src.app.models.category import Category
from src.app.models.product import Product
from src.app.workers.onec_client import OnecClient, OnecProduct
from src.app.workers.tasks import _sync_products_task


@pytest.fixture
def onec_products():
    return [
        OnecProduct(
            sku="1C-001",
            name="1C Product One",
            description="Description one",
            price=1000.0,
            stock=10,
            category_name="1C Category",
            is_active=True,
        ),
        OnecProduct(
            sku="1C-002",
            name="1C Product Two",
            description="Description two",
            price=2000.0,
            stock=20,
            category_name="1C Category",
            is_active=True,
        ),
    ]


class TestOnecClient:
    def test_get_products_parses_response(self):
        with patch("src.app.workers.onec_client.requests.request") as mock_request:
            mock_request.return_value.json.return_value = [
                {
                    "sku": "SKU-1",
                    "name": "Product 1",
                    "description": "Desc",
                    "price": 500,
                    "stock": 5,
                    "category_name": "Cat",
                    "is_active": True,
                }
            ]
            mock_request.return_value.raise_for_status = lambda: None

            client = OnecClient(base_url="http://1c.test", api_key="key")
            products = client.get_products()

        assert len(products) == 1
        assert products[0].sku == "SKU-1"
        assert products[0].price == 500.0

    def test_get_products_returns_empty_when_no_url(self):
        client = OnecClient(base_url=None, api_key=None)
        assert client.get_products() == []


class TestSyncProductsTask:
    @pytest.mark.asyncio
    async def test_sync_creates_new_products(
        self, test_session, test_supplier, onec_products
    ):
        with patch("src.app.workers.tasks.SEED_SUPPLIER_API_KEY", "test-api-key-123"):
            with patch.object(OnecClient, "get_products", return_value=onec_products):
                result = await _sync_products_task(test_session)

        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["errors"] == 0

        product1 = await test_session.get(Product, 1)
        assert product1 is not None
        assert product1.sku == "1C-001"
        assert product1.name == "1C Product One"
        assert product1.price == 1000.0
        assert product1.stock == 10

        category = await test_session.get(Category, 1)
        assert category is not None
        assert category.name == "1C Category"

    @pytest.mark.asyncio
    async def test_sync_updates_existing_product(
        self, test_session, test_supplier, onec_products
    ):
        with patch("src.app.workers.tasks.SEED_SUPPLIER_API_KEY", "test-api-key-123"):
            # First sync
            with patch.object(OnecClient, "get_products", return_value=onec_products):
                await _sync_products_task(test_session)

            # Second sync with changed price/stock
            updated = [
                OnecProduct(
                    sku="1C-001",
                    name="1C Product One Updated",
                    description="Updated desc",
                    price=1500.0,
                    stock=5,
                    category_name="1C Category Updated",
                    is_active=True,
                )
            ]
            with patch.object(OnecClient, "get_products", return_value=updated):
                result = await _sync_products_task(test_session)

        assert result["created"] == 0
        assert result["updated"] == 1

        product1 = await test_session.get(Product, 1)
        assert product1.name == "1C Product One Updated"
        assert product1.price == 1500.0
        assert product1.stock == 5

    @pytest.mark.asyncio
    async def test_sync_deactivates_missing_products(
        self, test_session, test_supplier, onec_products
    ):
        with patch("src.app.workers.tasks.SEED_SUPPLIER_API_KEY", "test-api-key-123"):
            # First sync creates two products
            with patch.object(OnecClient, "get_products", return_value=onec_products):
                await _sync_products_task(test_session)

            # Second sync returns only first product
            with patch.object(
                OnecClient, "get_products", return_value=[onec_products[0]]
            ):
                result = await _sync_products_task(test_session)

        assert result["deactivated"] == 1

        product2 = await test_session.get(Product, 2)
        assert product2.is_active is False
