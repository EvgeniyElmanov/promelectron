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
    assert product.full_name == "Smartphone X 256GB Black"
    assert product.article == "PHONE-001"
    assert product.code == "000000001"
    # У реальных товаров Parent_Key нулевой GUID → None (FORMAT_MAP.md §2)
    assert product.parent_key is None
    # Категория — по КатегорияНоменклатуры_Key
    assert product.category_key == "22222222-2222-2222-2222-222222222222"
    assert product.is_folder is False
    assert product.item_type == "Запас"
    # Вес в кг → граммы
    assert product.weight_grams == 250
    assert product.deletion_mark is False


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
    """Фильтр остатков — по СтруктурнаяЕдиница_Key (реальная УНФ), не Склад_Key."""
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


def test_production_http_url_rejected(monkeypatch):
    """В production ONEC_API_URL обязан быть https (SSRF-guard)."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    patched = replace(settings, onec_allow_insecure_http=False)
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    with pytest.raises(OnecClientError, match="https"):
        OnecClient(base_url="http://promelectron-onec-mock:8100/odata/standard.odata")


def test_production_http_url_allowed_with_insecure_flag(monkeypatch):
    """ONEC_ALLOW_INSECURE_HTTP=true — escape hatch для мока на test-стенде."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    patched = replace(settings, onec_allow_insecure_http=True)
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    client = OnecClient(base_url="http://promelectron-onec-mock:8100/odata/standard.odata")
    assert client.base_url == "http://promelectron-onec-mock:8100/odata/standard.odata"


def test_production_https_url_accepted(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    patched = replace(settings, onec_allow_insecure_http=False)
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    client = OnecClient(base_url="https://1c.example.com/unf/odata/standard.odata/")
    assert client.base_url == "https://1c.example.com/unf/odata/standard.odata"


@pytest.mark.asyncio
async def test_get_prices_without_price_type_key_fetches_all(client):
    """D-04: без price_type_key запрос идёт без $filter — тянем все виды цен."""
    prices = await client.get_prices()
    assert len(prices) == 3
    price_types = {p.price_type_key for p in prices}
    assert price_types == {
        "77777777-7777-7777-7777-777777777777",
        "88888888-8888-8888-8888-888888888888",
    }


@pytest.mark.asyncio
async def test_invalid_price_type_key_raises(onec_mock_server, monkeypatch):
    """GUID-валидация — только для явно переданного price_type_key (D-04)."""
    patched = replace(
        settings,
        onec_api_url=onec_mock_server,
    )
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)
    async with OnecClient() as c:
        with pytest.raises(OnecClientError):
            await c.get_prices("not-a-guid")


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


@pytest.mark.asyncio
async def test_get_attribute_definitions(client):
    definitions = await client.get_all_attribute_definitions()
    assert len(definitions) == 2
    color = next(d for d in definitions if d.ref_key == "dddddddd-dddd-dddd-dddd-dddddddddddd")
    # Имя — Заголовок, fallback Description
    assert color.name == "Цвет корпуса"
    assert color.value_type == "CatalogRef.ЗначенияСвойствОбъектов"
    power = next(d for d in definitions if d.ref_key == "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    assert power.name == "Мощность"
    assert power.value_type == "Number"


@pytest.mark.asyncio
async def test_get_attribute_values(client):
    values = await client.get_all_attribute_values()
    assert len(values) == 2
    assert {v.description for v in values} == {"Чёрный", "Белый"}
    # Фильтр по Owner_Key
    filtered = await client.get_all_attribute_values("dddddddd-dddd-dddd-dddd-dddddddddddd")
    assert len(filtered) == 2


@pytest.mark.asyncio
async def test_get_product_attributes(client):
    rows = await client.get_all_product_attributes()
    assert len(rows) == 3
    enum_row = next(r for r in rows if r.line_number == "1" and r.product_key.startswith("aaaaaaaa"))
    assert enum_row.value_key == "ffffffff-ffff-ffff-ffff-ffffffffffff"
    assert enum_row.value_type_name == "StandardODATA.Catalog_ЗначенияСвойствОбъектов"
    text_row = next(r for r in rows if r.line_number == "2")
    # Нулевой GUID значения → None, значение — в ТекстоваяСтрока
    assert text_row.value_key is None
    assert text_row.text_value == "65 Вт"
    # Фильтр по Ref_Key (guid'' форма)
    filtered = await client.get_all_product_attributes("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert len(filtered) == 2


@pytest.mark.asyncio
async def test_get_product_files(client):
    files = await client.get_all_product_files()
    assert len(files) == 3
    by_ref = {f.ref_key: f for f in files}
    assert by_ref["34343434-3434-3434-3434-343434343434"].extension == "jpg"
    assert by_ref["56565656-5656-5656-5656-565656565656"].deletion_mark is True
    filtered = await client.get_all_product_files("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert len(filtered) == 3


@pytest.mark.asyncio
async def test_download_file_binary(client):
    binary = await client.download_file_binary("34343434-3434-3434-3434-343434343434")
    assert binary.startswith(b"\xff\xd8\xff\xe0")
    with pytest.raises(OnecClientError):
        await client.download_file_binary("00000000-0000-0000-0000-000000000042")


@pytest.mark.asyncio
async def test_get_all_stock_balance_aggregates_across_pages(client, monkeypatch):
    """Строки баланса одного товара на разных страницах суммируются в одну запись."""
    from tests.mocks import onec_server

    monkeypatch.setattr(
        onec_server,
        "STOCKS",
        [
            {
                "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "СтруктурнаяЕдиница_Key": "99999999-9999-9999-9999-999999999999",
                "КоличествоBalance": -6,
            },
            {
                "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "СтруктурнаяЕдиница_Key": "00000000-0000-0000-0000-000000000001",
                "КоличествоBalance": 63,
            },
        ],
    )
    # page_size=1: две строки товара гарантированно на разных страницах
    stocks = await client.get_all_stock_balance(page_size=1)
    assert len(stocks) == 1
    assert stocks[0].product_key == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert stocks[0].quantity == 57
    # Без фильтра по складу warehouse_key сбрасывается
    assert stocks[0].warehouse_key is None

    # С фильтром по складу — страницы одного склада, ключ сохраняется
    filtered = await client.get_all_stock_balance(
        "99999999-9999-9999-9999-999999999999", page_size=1
    )
    assert len(filtered) == 1
    assert filtered[0].quantity == -6
    assert filtered[0].warehouse_key == "99999999-9999-9999-9999-999999999999"


@pytest.mark.asyncio
async def test_get_all_stock_balance_negative_not_clamped_in_client(client, monkeypatch):
    """Отрицательный итог клиент не клампит — это обязанность apply_stock_change (B-02)."""
    from tests.mocks import onec_server

    monkeypatch.setattr(
        onec_server,
        "STOCKS",
        [
            {
                "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "СтруктурнаяЕдиница_Key": "99999999-9999-9999-9999-999999999999",
                "КоличествоBalance": -6,
            },
        ],
    )
    stocks = await client.get_all_stock_balance()
    assert len(stocks) == 1
    assert stocks[0].quantity == -6
