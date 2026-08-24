"""Acceptance Criteria задачи product-prices-table.

Таблица product_prices: все виды цен 1С хранятся без потерь, наружу читается
только сайтовый вид (ONEC_SITE_PRICE_TYPE, в тестах — default "site").
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.app.models.onec_sync import OnecChangeLog
from src.app.models.order import OrderItem
from src.app.models.product_price import ProductPrice
from src.app.models.supplier import Supplier
from src.app.schemas.order import GuestOrderCreate, GuestOrderItemCreate
from src.app.services.onec_sync_service import handle_onec_apply_changes
from src.app.services.order_service import OrderService
from src.app.services.search_indexing import build_product_documents
from tests.conftest import make_product

SITE = "site"  # default settings.onec_site_price_type в тестовом окружении
COST = "sebestoimost"  # несайтовый вид цены (себестоимость)


async def _supplier_id(test_session, test_supplier) -> int:
    result = await test_session.execute(
        select(Supplier).where(Supplier.user_id == test_supplier.id)
    )
    return result.scalar_one().id


async def _apply_changes(test_session, entity_type: str, changes: list[dict]) -> None:
    """Прогнать батч changes через webhook/change-log path (job handler)."""
    payload = {
        "batch_id": str(uuid4()),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "base_name": "test-base",
        "entity_type": entity_type,
        "changes": changes,
    }
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type=entity_type,
        payload=payload,
        status="pending",
        checksum=f"checksum-{uuid4().hex[:12]}",
    )
    test_session.add(log)
    await test_session.flush()
    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()


async def _price_rows(test_session, product_id: int) -> dict[str, ProductPrice]:
    result = await test_session.execute(
        select(ProductPrice).where(ProductPrice.product_id == product_id)
    )
    return {row.price_type: row for row in result.scalars().all()}


def _price_change(onec_id: str, price: float, price_type: str, version: datetime) -> dict:
    return {
        "external_id": onec_id,
        "action": "update",
        "version": version.isoformat(),
        "data": {"price": price, "price_type_key": price_type},
    }


# ─── Webhook/change-log path ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_two_price_types_not_overwritten(
    test_session, test_supplier
):
    """AC: два вида цены по одному товару — две строки, не перезатираются."""
    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        onec_id="1c-pp-multi",
        name="Multi Price Product",
        price=None,
        stock=10,
        supplier_id=supplier_id,
        is_active=True,
    )
    await test_session.commit()
    version = datetime.now(timezone.utc)

    await _apply_changes(
        test_session,
        "price",
        [
            _price_change("1c-pp-multi", 350.0, SITE, version),
            _price_change("1c-pp-multi", 120.0, COST, version),
        ],
    )

    rows = await _price_rows(test_session, product.id)
    assert set(rows) == {SITE, COST}
    assert rows[SITE].price == Decimal("350.00")
    assert rows[COST].price == Decimal("120.00")

    # Обновление сайтового вида не трогает себестоимость
    newer = version + timedelta(minutes=1)
    await _apply_changes(
        test_session, "price", [_price_change("1c-pp-multi", 399.0, SITE, newer)]
    )
    rows = await _price_rows(test_session, product.id)
    assert rows[SITE].price == Decimal("399.00")
    assert rows[COST].price == Decimal("120.00")


@pytest.mark.asyncio
async def test_webhook_per_row_staleness(test_session, test_supplier):
    """AC: старый change (version <= onec_sync_at) по одному виду цены
    не трогает ни этот, ни другой вид."""
    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        onec_id="1c-pp-stale",
        name="Stale Price Product",
        price=None,
        stock=10,
        supplier_id=supplier_id,
        is_active=True,
    )
    await test_session.commit()
    version_new = datetime.now(timezone.utc)
    version_old = version_new - timedelta(days=1)

    await _apply_changes(
        test_session,
        "price",
        [
            _price_change("1c-pp-stale", 350.0, SITE, version_new),
            _price_change("1c-pp-stale", 120.0, COST, version_new),
        ],
    )
    # Старый change по сайтовому виду — должен быть проигнорирован
    await _apply_changes(
        test_session, "price", [_price_change("1c-pp-stale", 999.0, SITE, version_old)]
    )

    rows = await _price_rows(test_session, product.id)
    assert rows[SITE].price == Decimal("350.00")
    assert rows[SITE].onec_sync_at == version_new
    assert rows[COST].price == Decimal("120.00")


@pytest.mark.asyncio
async def test_webhook_non_positive_price_skipped(test_session, test_supplier):
    """B-01: цена ≤ 0 из change-log не пишется."""
    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        onec_id="1c-pp-zero",
        name="Zero Price Product",
        price=100.0,
        stock=10,
        supplier_id=supplier_id,
        is_active=True,
    )
    await test_session.commit()

    await _apply_changes(
        test_session,
        "price",
        [_price_change("1c-pp-zero", 0.0, SITE, datetime.now(timezone.utc))],
    )

    rows = await _price_rows(test_session, product.id)
    assert rows[SITE].price == Decimal("100.00")


@pytest.mark.asyncio
async def test_webhook_null_price_skipped(test_session, test_supplier):
    """F002: "price": null из внешнего JSON — warning + skip, батч не падает."""
    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        onec_id="1c-pp-null",
        name="Null Price Product",
        price=100.0,
        stock=10,
        supplier_id=supplier_id,
        is_active=True,
    )
    await test_session.commit()
    version = datetime.now(timezone.utc)

    null_change = {
        "external_id": "1c-pp-null",
        "action": "update",
        "version": version.isoformat(),
        "data": {"price": None, "price_type_key": SITE},
    }
    valid_change = _price_change("1c-pp-null", 250.0, COST, version)
    await _apply_changes(test_session, "price", [null_change, valid_change])

    rows = await _price_rows(test_session, product.id)
    assert rows[SITE].price == Decimal("100.00")  # сайтовая цена не изменилась
    assert rows[COST].price == Decimal("250.00")  # остаток батча применился


# ─── Каталог: фильтры, сортировка, null для бесценных ─────────────────────────


@pytest.fixture
async def priced_products(test_session, test_supplier, test_category):
    supplier_id = await _supplier_id(test_session, test_supplier)
    products = {}
    for name, price in [("Price Low", 30.0), ("Price Mid", 60.0), ("Price High", 90.0)]:
        products[name] = await make_product(
            test_session,
            name=name,
            price=price,
            stock=10,
            supplier_id=supplier_id,
            category_id=test_category.id,
            is_active=True,
        )
    products["Unpriced"] = await make_product(
        test_session,
        name="Unpriced Product",
        price=None,
        stock=10,
        supplier_id=supplier_id,
        category_id=test_category.id,
        is_active=True,
    )
    await test_session.commit()
    return products


@pytest.mark.asyncio
async def test_catalog_price_filter_excludes_unpriced(client, priced_products):
    """AC: min_price/max_price — через подзапрос сайтовой цены; бесценные вне фильтра."""
    response = await client.get("/api/v1/products/?min_price=40&max_price=80")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["Price Mid"]


@pytest.mark.asyncio
async def test_catalog_price_sort_unpriced_last(client, priced_products):
    """AC: price_asc/price_desc — бесценные всегда в конце (nulls_last)."""
    response = await client.get("/api/v1/products/?sort_by=price_asc")
    items = response.json()["items"]
    assert [i["price"] for i in items] == [30.0, 60.0, 90.0, None]

    response = await client.get("/api/v1/products/?sort_by=price_desc")
    items = response.json()["items"]
    assert [i["price"] for i in items] == [90.0, 60.0, 30.0, None]


@pytest.mark.asyncio
async def test_catalog_unpriced_product_price_null(client, priced_products):
    """AC: бесценный товар → price: null в списке и деталке."""
    unpriced_id = priced_products["Unpriced"].id

    response = await client.get("/api/v1/products/")
    item = next(i for i in response.json()["items"] if i["id"] == unpriced_id)
    assert item["price"] is None

    response = await client.get(f"/api/v1/products/{unpriced_id}")
    assert response.status_code == 200
    assert response.json()["price"] is None

    response = await client.get(f"/api/v1/products/{unpriced_id}/detail")
    assert response.status_code == 200
    assert response.json()["price"] is None


# ─── Заказ: снапшот сайтовой цены, 400 для бесценного ─────────────────────────


@pytest.mark.asyncio
async def test_order_snapshots_site_price(
    client, test_user, user_token, test_session, test_supplier, test_category,
    cdek_delivery_payload,
):
    """AC: заказ снапшотит сайтовую цену в price_at_time (не себестоимость)."""
    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        name="Snapshot Product",
        price=99.99,
        stock=10,
        supplier_id=supplier_id,
        category_id=test_category.id,
        is_active=True,
    )
    # Несайтовый вид цены — не должен попасть в заказ
    test_session.add(
        ProductPrice(product_id=product.id, price_type=COST, price=Decimal("10.00"))
    )
    await test_session.commit()

    await client.post(
        "/api/v1/cart/add",
        json={"product_id": product.id, "quantity": 2},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    order_resp = await client.post(
        "/api/v1/orders/create/",
        json={
            "cdek_delivery": cdek_delivery_payload,
            "recipient_first_name": "Тест",
            "recipient_last_name": "Пользователь",
            "recipient_phone": "+79990001122",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert order_resp.status_code == 200

    order_item = (
        await test_session.execute(
            select(OrderItem).where(OrderItem.product_id == product.id)
        )
    ).scalar_one()
    assert order_item.price_at_time == Decimal("99.99")


@pytest.mark.asyncio
async def test_order_unpriced_product_rejected(
    client, test_user, user_token, test_session, test_supplier, test_category,
    cdek_delivery_payload,
):
    """AC: товар без сайтовой цены не продаётся — 400 при создании заказа."""
    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        name="Unpriced Orderable",
        price=None,
        stock=10,
        supplier_id=supplier_id,
        category_id=test_category.id,
        is_active=True,
    )
    await test_session.commit()

    await client.post(
        "/api/v1/cart/add",
        json={"product_id": product.id, "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    order_resp = await client.post(
        "/api/v1/orders/create/",
        json={
            "cdek_delivery": cdek_delivery_payload,
            "recipient_first_name": "Тест",
            "recipient_last_name": "Пользователь",
            "recipient_phone": "+79990001122",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert order_resp.status_code == 400
    assert "temporarily unavailable" in order_resp.json()["detail"]


@pytest.mark.asyncio
async def test_guest_order_unpriced_product_rejected(
    test_session, test_supplier, test_category, cdek_delivery_payload
):
    """AC: гостевой заказ бесценного товара — тоже отказ (через сервис,
    API create-guest отключён — 410)."""
    from fastapi import HTTPException

    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        name="Guest Unpriced",
        price=None,
        stock=10,
        supplier_id=supplier_id,
        category_id=test_category.id,
        is_active=True,
    )
    await test_session.commit()

    order_data = GuestOrderCreate(
        items=[GuestOrderItemCreate(product_id=product.id, quantity=1)],
        cdek_delivery=cdek_delivery_payload,
        guest_email="guest@example.com",
        recipient_phone="+79990001122",
        recipient_first_name="Иван",
        recipient_last_name="Гость",
    )
    with pytest.raises(HTTPException) as exc_info:
        await OrderService.create_guest_order(order_data=order_data, db=test_session)
    assert exc_info.value.status_code == 400
    assert "temporarily unavailable" in exc_info.value.detail


# ─── Приватность несайтовых видов цен ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_non_site_price_not_visible(
    client, test_user, user_token, test_session, test_supplier, test_category
):
    """AC: несайтовый price_type не виден в списке, деталке, корзине, поиске."""
    supplier_id = await _supplier_id(test_session, test_supplier)
    product = await make_product(
        test_session,
        name="Privacy Product",
        price=350.0,
        stock=10,
        supplier_id=supplier_id,
        category_id=test_category.id,
        is_active=True,
    )
    test_session.add(
        ProductPrice(product_id=product.id, price_type=COST, price=Decimal("120.00"))
    )
    await test_session.commit()

    response = await client.get("/api/v1/products/")
    item = next(i for i in response.json()["items"] if i["id"] == product.id)
    assert item["price"] == 350.0

    response = await client.get(f"/api/v1/products/{product.id}/detail")
    assert response.json()["price"] == 350.0

    await client.post(
        "/api/v1/cart/add",
        json={"product_id": product.id, "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    response = await client.get(
        "/api/v1/cart/", headers={"Authorization": f"Bearer {user_token}"}
    )
    cart_item = response.json()["items"][0]
    assert cart_item["product"]["price"] == 350.0

    # Поисковый документ — тоже только сайтовая цена
    documents, _ = await build_product_documents(test_session, [product.id])
    assert documents[0]["price"] == 350.0


# ─── Supplier create/update: валидация и запись сайтовой строки ───────────────


@pytest.mark.asyncio
async def test_supplier_create_product_non_positive_price_422(
    client, test_supplier, test_category
):
    """AC: price ≤ 0 при создании — 422 (Field gt=0)."""
    from src.app.utils.auth import create_access_token

    token = create_access_token(
        data={"sub": str(test_supplier.id), "role": test_supplier.role.value}
    )
    for bad_price in (0, -5):
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": f"Bad Price {bad_price}",
                "price": bad_price,
                "stock": 5,
                "category_id": test_category.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_supplier_create_and_update_write_site_price(
    client, test_session, test_supplier, test_category
):
    """AC: create/update поставщика пишут сайтовую строку product_prices."""
    from src.app.utils.auth import create_access_token

    token = create_access_token(
        data={"sub": str(test_supplier.id), "role": test_supplier.role.value}
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/products/",
        json={
            "name": "Supplier Priced",
            "price": 29.99,
            "stock": 5,
            "category_id": test_category.id,
        },
        headers=headers,
    )
    assert response.status_code == 200
    product_id = response.json()["id"]
    assert response.json()["price"] == 29.99

    rows = await _price_rows(test_session, product_id)
    assert set(rows) == {SITE}
    assert rows[SITE].price == Decimal("29.99")

    response = await client.put(
        f"/api/v1/products/{product_id}", json={"price": 39.99}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["price"] == 39.99

    rows = await _price_rows(test_session, product_id)
    assert set(rows) == {SITE}
    assert rows[SITE].price == Decimal("39.99")

    # Update с price ≤ 0 — 422
    response = await client.put(
        f"/api/v1/products/{product_id}", json={"price": 0}, headers=headers
    )
    assert response.status_code == 422
