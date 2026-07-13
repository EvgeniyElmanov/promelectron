from dataclasses import replace
from decimal import Decimal

import pytest

from src.app.core.config import settings
from src.app.schemas.onec import (
    OnecCategoryOdata,
    OnecPriceOdata,
    OnecProductOdata,
    OnecStockOdata,
)
from src.app.workers.onec_client import OnecClient, OnecClientAuthError, OnecClientError


@pytest.fixture
def onec_client_settings(onec_mock_server):
    return {
        "onec_api_url": onec_mock_server,
        "onec_login": "test-user",
        "onec_password": "test-pass",
    }


@pytest.fixture
async def client(onec_client_settings, monkeypatch):
    patched = replace(settings, **onec_client_settings)
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    async with OnecClient() as c:
        yield c


@pytest.mark.asyncio
async def test_get_categories(client):
    categories = await client.get_categories()
    assert len(categories) == 2
    assert all(isinstance(c, OnecCategoryOdata) for c in categories)
    assert categories[0].ref_key == "11111111-1111-1111-1111-111111111111"
    assert categories[0].description == "Electronics"
    assert categories[1].parent_key == categories[0].ref_key


@pytest.mark.asyncio
async def test_get_products(client):
    products = await client.get_products()
    assert len(products) == 1
    product = products[0]
    assert isinstance(product, OnecProductOdata)
    assert product.ref_key == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert product.description == "Smartphone X"
    assert product.article == "PHONE-001"
    assert product.code == "000000001"
    assert product.parent_key == "22222222-2222-2222-2222-222222222222"
    assert product.is_folder is False
    assert product.item_type == "Запас"


@pytest.mark.asyncio
async def test_get_prices(client):
    prices = await client.get_prices("77777777-7777-7777-7777-777777777777")
    assert len(prices) == 2
    assert all(isinstance(p, OnecPriceOdata) for p in prices)
    assert prices[0].product_key == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert prices[0].price_type_key == "77777777-7777-7777-7777-777777777777"
    assert prices[0].price == Decimal("999.99")


@pytest.mark.asyncio
async def test_get_stock_balance_all_warehouses(client):
    stocks = await client.get_stock_balance()
    assert len(stocks) == 2
    assert all(isinstance(s, OnecStockOdata) for s in stocks)
    smartphone_stock = next(
        s for s in stocks if s.product_key == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )
    assert smartphone_stock.quantity == 20.0  # 12 + 8
    assert smartphone_stock.warehouse_key is None


@pytest.mark.asyncio
async def test_get_stock_balance_single_warehouse(client):
    stocks = await client.get_stock_balance("99999999-9999-9999-9999-999999999999")
    assert len(stocks) == 2
    assert all(isinstance(s, OnecStockOdata) for s in stocks)
    smartphone_stock = next(
        s for s in stocks if s.product_key == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )
    assert smartphone_stock.quantity == 12.0
    assert smartphone_stock.warehouse_key == "99999999-9999-9999-9999-999999999999"


@pytest.mark.asyncio
async def test_pagination(client):
    first_page = await client.get_categories(top=1, skip=0)
    assert len(first_page) == 1
    assert first_page[0].ref_key == "11111111-1111-1111-1111-111111111111"

    second_page = await client.get_categories(top=1, skip=1)
    assert len(second_page) == 1
    assert second_page[0].ref_key == "22222222-2222-2222-2222-222222222222"


@pytest.mark.asyncio
async def test_get_all_categories(client):
    categories = await client.get_all_categories()
    assert len(categories) == 2


@pytest.mark.asyncio
async def test_unconfigured_client_raises_error(monkeypatch):
    patched = replace(settings, onec_api_url=None, onec_login=None, onec_password=None)
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    with pytest.raises(OnecClientError):
        OnecClient()


@pytest.mark.asyncio
async def test_invalid_price_type_key_raises(onec_mock_server, monkeypatch):
    patched = replace(
        settings,
        onec_api_url=onec_mock_server,
        onec_price_type_key="not-a-guid",
    )
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    async with OnecClient() as c:
        with pytest.raises(OnecClientError):
            await c.get_prices()


@pytest.mark.asyncio
async def test_invalid_warehouse_key_raises(onec_mock_server, monkeypatch):
    patched = replace(
        settings,
        onec_api_url=onec_mock_server,
        onec_warehouse_key="not-a-guid",
    )
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    async with OnecClient() as c:
        with pytest.raises(OnecClientError):
            await c.get_stock_balance()


@pytest.mark.asyncio
async def test_auth_error(onec_mock_server, monkeypatch):
    patched = replace(
        settings,
        onec_api_url=onec_mock_server,
        onec_login="wrong",
        onec_password="wrong",
    )
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    async with OnecClient() as c:
        with pytest.raises(OnecClientAuthError):
            await c.get_categories()
