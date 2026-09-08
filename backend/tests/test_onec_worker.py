from dataclasses import replace
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.app.models.category import Category
from src.app.models.job import Job
from src.app.models.onec_sync import OnecChangeLog
from src.app.models.product import Product
from src.app.models.product_price import ProductPrice
from src.app.models.supplier import Supplier
from src.app.services.onec_sync_service import handle_onec_apply_changes, run_onec_full_sync
from src.app.core.config import settings
from tests.conftest import make_product


def _build_payload(entity_type: str, changes: list[dict]) -> dict:
    return {
        "batch_id": str(uuid4()),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "base_name": "test-base",
        "entity_type": entity_type,
        "changes": changes,
    }


@pytest.fixture
async def supplier_id(test_session, test_supplier):
    result = await test_session.execute(
        select(Supplier).where(Supplier.user_id == test_supplier.id)
    )
    supplier = result.scalar_one()
    return supplier.id


@pytest.mark.asyncio
async def test_onec_apply_product_change(test_session, supplier_id):
    version = datetime.now(timezone.utc)
    payload = _build_payload(
        "product",
        [
            {
                "external_id": "1c-prod-100",
                "action": "create",
                "version": version.isoformat(),
                "data": {
                    "name": "Applied Product",
                    "description": "From 1C",
                    "sku": "APP-001",
                    "price": 299.99,
                    "stock": 12,
                    "is_active": True,
                    "supplier_id": supplier_id,
                },
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="product",
        payload=payload,
        status="pending",
        checksum="checksum-1",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    result = await test_session.execute(
        select(Product).where(Product.onec_id == "1c-prod-100")
    )
    product = result.scalar_one()
    assert product.name == "Applied Product"
    assert product.description == "From 1C"
    assert product.sku == "APP-001"
    # Товарный change больше не несёт цену (D-06): ключ price в data игнорируется,
    # строка product_prices не создаётся — сайтовая цена None
    assert product.price is None
    assert product.stock == 12
    assert product.is_active is True
    assert product.onec_sync_at == version

    await test_session.refresh(log)
    assert log.status == "done"
    assert log.applied_at is not None


@pytest.mark.asyncio
async def test_onec_apply_category_change(test_session):
    version = datetime.now(timezone.utc)
    payload = _build_payload(
        "category",
        [
            {
                "external_id": "1c-cat-200",
                "action": "create",
                "version": version.isoformat(),
                "data": {"name": "Applied Category", "is_active": True},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="category",
        payload=payload,
        status="pending",
        checksum="checksum-2",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    result = await test_session.execute(
        select(Category).where(Category.onec_id == "1c-cat-200")
    )
    category = result.scalar_one()
    assert category.name == "Applied Category"
    assert category.is_active is True
    assert category.onec_sync_at == version

    await test_session.refresh(log)
    assert log.status == "done"


@pytest.mark.asyncio
async def test_onec_apply_category_delete(test_session):
    version = datetime.now(timezone.utc)
    payload = _build_payload(
        "category",
        [
            {
                "external_id": "1c-cat-300",
                "action": "create",
                "version": version.isoformat(),
                "data": {"name": "To Be Deleted", "is_active": True},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="category",
        payload=payload,
        status="pending",
        checksum="checksum-3",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    delete_version = version.replace(year=version.year + 1)
    delete_payload = _build_payload(
        "category",
        [
            {
                "external_id": "1c-cat-300",
                "action": "delete",
                "version": delete_version.isoformat(),
                "data": {},
            }
        ],
    )
    log2 = OnecChangeLog(
        batch_id=delete_payload["batch_id"],
        entity_type="category",
        payload=delete_payload,
        status="pending",
        checksum="checksum-4",
    )
    test_session.add(log2)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log2.id})
    await test_session.commit()

    result = await test_session.execute(
        select(Category).where(Category.onec_id == "1c-cat-300")
    )
    category = result.scalar_one()
    assert category.is_active is False
    assert category.name == "To Be Deleted"


@pytest.mark.asyncio
async def test_onec_apply_version_conflict_skips_stale_change(test_session, supplier_id):
    """Older change.version must not overwrite a newer entity.onec_sync_at."""
    newer_version = datetime.now(timezone.utc)
    older_version = newer_version.replace(year=newer_version.year - 1)
    external_id = "1c-prod-version-1"

    # 1. Apply a change with the newer version.
    payload_newer = _build_payload(
        "product",
        [
            {
                "external_id": external_id,
                "action": "create",
                "version": newer_version.isoformat(),
                "data": {
                    "name": "Newer Name",
                    "description": "Newer description",
                    "sku": "NEWER-001",
                    "price": 399.99,
                    "stock": 20,
                    "is_active": True,
                    "supplier_id": supplier_id,
                },
            }
        ],
    )
    log_newer = OnecChangeLog(
        batch_id=payload_newer["batch_id"],
        entity_type="product",
        payload=payload_newer,
        status="pending",
        checksum="checksum-version-newer",
    )
    test_session.add(log_newer)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log_newer.id})
    await test_session.commit()

    # 2. Apply a change with an older version.
    payload_older = _build_payload(
        "product",
        [
            {
                "external_id": external_id,
                "action": "update",
                "version": older_version.isoformat(),
                "data": {
                    "name": "Older Name",
                    "description": "Older description",
                    "sku": "OLDER-001",
                    "price": 1.99,
                    "stock": 1,
                    "is_active": False,
                },
            }
        ],
    )
    log_older = OnecChangeLog(
        batch_id=payload_older["batch_id"],
        entity_type="product",
        payload=payload_older,
        status="pending",
        checksum="checksum-version-older",
    )
    test_session.add(log_older)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log_older.id})
    await test_session.commit()

    # 3. Verify the entity still has the newer values.
    result = await test_session.execute(
        select(Product).where(Product.onec_id == external_id)
    )
    product = result.scalar_one()
    assert product.name == "Newer Name"
    assert product.description == "Newer description"
    assert product.sku == "NEWER-001"
    assert product.price is None  # товарный change цену не пишет (D-06)
    assert product.stock == 20
    assert product.is_active is True
    assert product.onec_sync_at == newer_version

    await test_session.refresh(log_older)
    assert log_older.status == "done"


@pytest.mark.asyncio
async def test_onec_apply_category_version_conflict_skips_stale_change(test_session):
    """Older change.version must not overwrite a newer category.onec_sync_at."""
    newer_version = datetime.now(timezone.utc)
    older_version = newer_version.replace(year=newer_version.year - 1)
    external_id = "1c-cat-version-1"

    payload_newer = _build_payload(
        "category",
        [
            {
                "external_id": external_id,
                "action": "create",
                "version": newer_version.isoformat(),
                "data": {"name": "Newer Category", "is_active": True},
            }
        ],
    )
    log_newer = OnecChangeLog(
        batch_id=payload_newer["batch_id"],
        entity_type="category",
        payload=payload_newer,
        status="pending",
        checksum="checksum-cat-version-newer",
    )
    test_session.add(log_newer)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log_newer.id})
    await test_session.commit()

    payload_older = _build_payload(
        "category",
        [
            {
                "external_id": external_id,
                "action": "update",
                "version": older_version.isoformat(),
                "data": {"name": "Older Category", "is_active": False},
            }
        ],
    )
    log_older = OnecChangeLog(
        batch_id=payload_older["batch_id"],
        entity_type="category",
        payload=payload_older,
        status="pending",
        checksum="checksum-cat-version-older",
    )
    test_session.add(log_older)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log_older.id})
    await test_session.commit()

    result = await test_session.execute(
        select(Category).where(Category.onec_id == external_id)
    )
    category = result.scalar_one()
    assert category.name == "Newer Category"
    assert category.is_active is True
    assert category.onec_sync_at == newer_version

    await test_session.refresh(log_older)
    assert log_older.status == "done"


@pytest.mark.asyncio
async def test_onec_apply_product_with_category_id(test_session, supplier_id):
    """Product creation with category_id as category onec_id must resolve to internal id."""
    version = datetime.now(timezone.utc)
    category_onec_id = "1c-cat-999"
    category = Category(onec_id=category_onec_id, name="Test Category", is_active=True)
    test_session.add(category)
    await test_session.flush()

    payload = _build_payload(
        "product",
        [
            {
                "external_id": "1c-prod-with-cat",
                "action": "create",
                "version": version.isoformat(),
                "data": {
                    "name": "Product With Category",
                    "description": "Has category",
                    "sku": "CAT-001",
                    "price": 199.99,
                    "stock": 5,
                    "is_active": True,
                    "supplier_id": supplier_id,
                    "category_id": category_onec_id,
                },
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="product",
        payload=payload,
        status="pending",
        checksum="checksum-cat-id",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    result = await test_session.execute(
        select(Product).where(Product.onec_id == "1c-prod-with-cat")
    )
    product = result.scalar_one()
    assert product.category_id == category.id
    assert product.name == "Product With Category"

    await test_session.refresh(log)
    assert log.status == "done"


@pytest.mark.asyncio
async def test_onec_apply_changes_per_change_isolation(test_session, supplier_id):
    """Битый change не валит батч: валидный применён, лог done со сводкой ошибок."""
    version = datetime.now(timezone.utc)
    payload = _build_payload(
        "product",
        [
            {
                "external_id": "1c-prod-valid",
                "action": "create",
                "version": version.isoformat(),
                "data": {
                    "name": "Valid Product",
                    "sku": "VALID-001",
                    "stock": 1,
                    "is_active": True,
                    "supplier_id": supplier_id,
                },
            },
            {
                "external_id": "1c-prod-invalid",
                "action": "create",
                "version": version.isoformat(),
                "data": {
                    "name": "Invalid Product",
                    "sku": "INVALID-001",
                    "stock": 1,
                    "is_active": True,
                    "supplier_id": supplier_id,
                    "category_id": "non-existent-onec-id",
                },
            },
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="product",
        payload=payload,
        status="pending",
        checksum="checksum-batch-rollback",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    # Валидный change применён несмотря на упавший соседний
    result = await test_session.execute(
        select(Product).where(Product.onec_id == "1c-prod-valid")
    )
    valid_product = result.scalar_one()
    assert valid_product.name == "Valid Product"
    assert valid_product.sku == "VALID-001"

    # Битый change не создал товар
    result = await test_session.execute(
        select(Product).where(Product.onec_id == "1c-prod-invalid")
    )
    assert result.scalar_one_or_none() is None

    await test_session.refresh(log)
    assert log.status == "done"
    assert "1 change(s) failed" in log.error_message
    assert "non-existent-onec-id" in log.error_message


@pytest.mark.asyncio
async def test_onec_apply_changes_all_failed_marks_failed(test_session, supplier_id):
    """Если не применился ни один change — батч failed, retry-семантика сохранена."""
    version = datetime.now(timezone.utc)
    payload = _build_payload(
        "product",
        [
            {
                "external_id": "1c-prod-broken",
                "action": "create",
                "version": version.isoformat(),
                "data": {
                    "name": "Broken Product",
                    "supplier_id": supplier_id,
                    "category_id": "non-existent-onec-id",
                },
            },
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="product",
        payload=payload,
        status="pending",
        checksum="checksum-batch-all-failed",
    )
    test_session.add(log)
    await test_session.flush()

    with pytest.raises(ValueError):
        await handle_onec_apply_changes(test_session, {"log_id": log.id})

    await test_session.commit()
    await test_session.refresh(log)
    assert log.status == "failed"
    assert log.error_message is not None
    assert log.retry_count == 1


@pytest.mark.asyncio
async def test_onec_apply_product_change_duplicate_sku(test_session, supplier_id):
    """Дубль Артикула из 1С: оба товара созданы, у второго sku=NULL (F002)."""
    version = datetime.now(timezone.utc)

    async def _apply(external_id: str, sku: str) -> None:
        payload = _build_payload(
            "product",
            [
                {
                    "external_id": external_id,
                    "action": "create",
                    "version": version.isoformat(),
                    "data": {
                        "name": f"Product {external_id} {sku}",
                        "sku": sku,
                        "supplier_id": supplier_id,
                    },
                }
            ],
        )
        log = OnecChangeLog(
            batch_id=payload["batch_id"],
            entity_type="product",
            payload=payload,
            status="pending",
            checksum=f"checksum-{external_id}",
        )
        test_session.add(log)
        await test_session.flush()
        await handle_onec_apply_changes(test_session, {"log_id": log.id})
        await test_session.commit()

    await _apply("1c-dup-1", "ТУТк-4/1 черная")
    await _apply("1c-dup-2", "ТУТк-4/1 черная")

    first = (
        await test_session.execute(select(Product).where(Product.onec_id == "1c-dup-1"))
    ).scalar_one()
    second = (
        await test_session.execute(select(Product).where(Product.onec_id == "1c-dup-2"))
    ).scalar_one()
    assert first.sku == "ТУТк-4/1 черная"
    assert second.sku is None
    # Оригинальный артикул сохраняется в name
    assert "ТУТк-4/1 черная" in second.name


@pytest.mark.asyncio
async def test_onec_apply_product_change_sku_strip(test_session, supplier_id):
    """Артикулы с хвостовыми пробелами из 1С нормализуются (strip) и дедупятся."""
    version = datetime.now(timezone.utc)

    async def _apply(external_id: str, sku: str) -> None:
        payload = _build_payload(
            "product",
            [
                {
                    "external_id": external_id,
                    "action": "create",
                    "version": version.isoformat(),
                    "data": {
                        "name": f"Product {external_id}",
                        "sku": sku,
                        "supplier_id": supplier_id,
                    },
                }
            ],
        )
        log = OnecChangeLog(
            batch_id=payload["batch_id"],
            entity_type="product",
            payload=payload,
            status="pending",
            checksum=f"checksum-{external_id}",
        )
        test_session.add(log)
        await test_session.flush()
        await handle_onec_apply_changes(test_session, {"log_id": log.id})
        await test_session.commit()

    await _apply("1c-strip-1", "JQC-3F-12VDC-1ZS         ")
    # То же значение с пробелами у другого Ref_Key — дубль после strip
    await _apply("1c-strip-2", "JQC-3F-12VDC-1ZS")

    first = (
        await test_session.execute(select(Product).where(Product.onec_id == "1c-strip-1"))
    ).scalar_one()
    second = (
        await test_session.execute(select(Product).where(Product.onec_id == "1c-strip-2"))
    ).scalar_one()
    assert first.sku == "JQC-3F-12VDC-1ZS"
    assert second.sku is None


@pytest.mark.asyncio
async def test_onec_apply_price_change(test_session, supplier_id):
    """Price change обновляет сайтовую строку product_prices (per-row staleness)."""
    version = datetime.now(timezone.utc)
    product = await make_product(
        test_session,
        onec_id="1c-prod-price",
        name="Price Product",
        sku="PRICE-001",
        price=100.0,
        stock=10,
        supplier_id=supplier_id,
        is_active=True,
    )
    await test_session.flush()

    payload = _build_payload(
        "price",
        [
            {
                "external_id": "1c-prod-price",
                "action": "update",
                "version": version.isoformat(),
                "data": {"price": 199.99},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="price",
        payload=payload,
        status="pending",
        checksum="checksum-price",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    await test_session.refresh(product)
    assert product.price == Decimal("199.99")
    # Ценовой change больше не трогает product.onec_sync_at (per-row staleness, D-06)
    assert product.onec_sync_at is None
    row = (
        await test_session.execute(
            select(ProductPrice).where(ProductPrice.product_id == product.id)
        )
    ).scalar_one()
    assert row.price == Decimal("199.99")
    assert row.onec_sync_at == version


@pytest.mark.asyncio
async def test_onec_apply_stock_change(test_session, supplier_id):
    """Stock change updates existing product stock."""
    version = datetime.now(timezone.utc)
    product = await make_product(
        test_session,
        onec_id="1c-prod-stock",
        name="Stock Product",
        sku="STOCK-001",
        price=100.0,
        stock=10,
        supplier_id=supplier_id,
        is_active=True,
    )
    await test_session.flush()

    payload = _build_payload(
        "stock",
        [
            {
                "external_id": "1c-prod-stock",
                "action": "update",
                "version": version.isoformat(),
                "data": {"stock": 42},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="stock",
        payload=payload,
        status="pending",
        checksum="checksum-stock",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    await test_session.refresh(product)
    assert product.stock == 42
    assert product.onec_sync_at == version


@pytest.mark.asyncio
async def test_onec_apply_stock_change_negative_clamped_to_zero(test_session, supplier_id):
    """Отрицательный остаток из 1С клампится в 0 (B-02)."""
    product = await make_product(
        test_session,
        onec_id="1c-prod-stock-neg",
        name="Negative Stock Product",
        sku="STOCK-NEG-001",
        price=100.0,
        stock=10,
        supplier_id=supplier_id,
        is_active=True,
    )
    await test_session.flush()

    payload = _build_payload(
        "stock",
        [
            {
                "external_id": "1c-prod-stock-neg",
                "action": "update",
                "version": datetime.now(timezone.utc).isoformat(),
                "data": {"stock": -6},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="stock",
        payload=payload,
        status="pending",
        checksum="checksum-stock-neg",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    await test_session.refresh(product)
    assert product.stock == 0


@pytest.mark.asyncio
async def test_onec_apply_order_status_change_skips(test_session, supplier_id, caplog):
    """order_status changes are accepted but skipped in Phase 1."""
    version = datetime.now(timezone.utc)
    payload = _build_payload(
        "order_status",
        [
            {
                "external_id": "order-123",
                "action": "update",
                "version": version.isoformat(),
                "data": {"status": "shipped"},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="order_status",
        payload=payload,
        status="pending",
        checksum="checksum-order-status",
    )
    test_session.add(log)
    await test_session.flush()

    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    await test_session.refresh(log)
    assert log.status == "done"
    assert "not implemented yet" in caplog.text


@pytest.mark.asyncio
async def test_run_onec_full_sync_creates_batches(
    test_session, onec_mock_server, monkeypatch, supplier_id
):
    """Pull fallback fetches from mock 1C and enqueues apply batches."""
    patched = replace(
        settings,
        onec_api_url=onec_mock_server,
        onec_login="test-user",
        onec_password="test-pass",
        onec_default_supplier_id=supplier_id,
    )
    monkeypatch.setattr("src.app.services.onec_sync_service.settings", patched)
    monkeypatch.setattr("src.app.workers.onec_client.settings", patched)

    await run_onec_full_sync(test_session, default_supplier_id=supplier_id)
    await test_session.commit()

    logs = await test_session.execute(select(OnecChangeLog))
    log_list = logs.scalars().all()
    entity_types = sorted(log.entity_type for log in log_list)
    # category, product, price, stock + product_attributes + product_images
    assert entity_types == [
        "category",
        "price",
        "product",
        "product_attributes",
        "product_images",
        "stock",
    ]

    jobs = await test_session.execute(select(Job).where(Job.job_type == "ONEC_APPLY_CHANGES"))
    job_list = jobs.scalars().all()
    assert len(job_list) == 6

    product_log = next(log for log in log_list if log.entity_type == "product")
    assert product_log.checksum is not None
    product_data = product_log.payload["changes"][0]["data"]
    assert product_data["supplier_id"] == supplier_id
    # Категория — по КатегорияНоменклатуры_Key, не Parent_Key
    assert product_data["category_id"] == "22222222-2222-2222-2222-222222222222"
    assert product_data["description"] == "Smartphone X 256GB Black"
    assert product_data["weight_grams"] == 250
    assert product_data["is_active"] is True

    # Определения характеристик применяются напрямую
    from src.app.models.attribute import Attribute

    attributes = await test_session.execute(select(Attribute))
    attribute_list = attributes.scalars().all()
    assert {a.name for a in attribute_list} == {"Цвет корпуса", "Мощность"}

    # Значение enum-характеристики разрешено в Description на этапе синка
    attrs_log = next(log for log in log_list if log.entity_type == "product_attributes")
    attr_changes = {
        c["external_id"]: c["data"]["attributes"] for c in attrs_log.payload["changes"]
    }
    smartphone_attrs = attr_changes["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]
    assert smartphone_attrs[0]["attribute_key"] == "dddddddd-dddd-dddd-dddd-dddddddddddd"
    assert smartphone_attrs[0]["value"] == "Чёрный"
    assert smartphone_attrs[1]["value"] == "65 Вт"
    # Строка для товара вне каталога тоже попала в батч — пропуск на apply
    assert "99999999-8888-7777-6666-555555555555" in attr_changes

    # Изображения: DeletionMark-файл пропущен, порядок по Description
    images_log = next(log for log in log_list if log.entity_type == "product_images")
    image_urls = images_log.payload["changes"][0]["data"]["images"]
    assert image_urls == [
        "/uploads/onec/45454545-4545-4545-4545-454545454545.png",
        "/uploads/onec/34343434-3434-3434-3434-343434343434.jpg",
    ]


@pytest.mark.asyncio
async def test_onec_apply_product_attributes_change(test_session, supplier_id):
    """product_attributes: upsert ProductAttributeValue, идемпотентно."""
    from src.app.models.attribute import Attribute, AttributeValueType, ProductAttributeValue

    product = await make_product(
        test_session,
        name="Attr Product",
        sku="ATTR-001",
        onec_id="1c-attr-1",
        supplier_id=supplier_id,
        stock=0,
        is_active=True,
    )
    attribute = Attribute(
        code="1c-attr-def-1",
        onec_id="1c-attr-def-1",
        name="Мощность",
        value_type=AttributeValueType.string,
    )
    test_session.add(attribute)
    await test_session.commit()

    def _payload():
        return _build_payload(
            "product_attributes",
            [
                {
                    "external_id": "1c-attr-1",
                    "action": "update",
                    "version": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "attributes": [
                            {"attribute_key": "1c-attr-def-1", "value": "65 Вт"},
                            {"attribute_key": "1c-attr-unknown", "value": "x"},
                        ]
                    },
                }
            ],
        )

    for _ in range(2):  # повторное применение не плодит дубли
        payload = _payload()
        log = OnecChangeLog(
            batch_id=payload["batch_id"],
            entity_type="product_attributes",
            payload=payload,
            status="pending",
            checksum=f"checksum-attrs-{uuid4()}",
        )
        test_session.add(log)
        await test_session.flush()
        await handle_onec_apply_changes(test_session, {"log_id": log.id})
        await test_session.commit()

    values = await test_session.execute(
        select(ProductAttributeValue).where(
            ProductAttributeValue.product_id == product.id
        )
    )
    value_list = values.scalars().all()
    assert len(value_list) == 2
    by_attr = {v.attribute_id: v for v in value_list}
    # «65 Вт» нормализовано в число + единицу (parse_value_with_unit, D-10)
    assert by_attr[attribute.id].value_number == 65
    await test_session.refresh(attribute)
    assert attribute.unit == "Вт"
    # Неизвестное определение — auto-create заглушкой (D-05)
    unknown = await test_session.execute(
        select(Attribute).where(Attribute.onec_id == "1c-attr-unknown")
    )
    unknown_attr = unknown.scalar_one()
    assert unknown_attr.is_filterable is False
    assert by_attr[unknown_attr.id].value_text == "x"

    # Неизвестный товар — молча пропускается, батч done
    payload = _build_payload(
        "product_attributes",
        [
            {
                "external_id": "1c-no-such-product",
                "action": "update",
                "version": datetime.now(timezone.utc).isoformat(),
                "data": {"attributes": [{"attribute_key": "1c-attr-def-1", "value": "1"}]},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="product_attributes",
        payload=payload,
        status="pending",
        checksum=f"checksum-attrs-{uuid4()}",
    )
    test_session.add(log)
    await test_session.flush()
    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()
    await test_session.refresh(log)
    assert log.status == "done"


@pytest.mark.asyncio
async def test_onec_apply_product_images_change(test_session, supplier_id):
    """product_images: merge URL в products.images без дублей."""
    product = await make_product(
        test_session,
        name="Img Product",
        sku="IMG-001",
        onec_id="1c-img-1",
        supplier_id=supplier_id,
        stock=0,
        is_active=True,
    )
    product.images = ["/uploads/onec/existing.jpg"]
    await test_session.commit()

    def _payload():
        return _build_payload(
            "product_images",
            [
                {
                    "external_id": "1c-img-1",
                    "action": "update",
                    "version": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "images": [
                            "/uploads/onec/existing.jpg",
                            "/uploads/onec/new.jpg",
                        ]
                    },
                }
            ],
        )

    for _ in range(2):
        payload = _payload()
        log = OnecChangeLog(
            batch_id=payload["batch_id"],
            entity_type="product_images",
            payload=payload,
            status="pending",
            checksum=f"checksum-imgs-{uuid4()}",
        )
        test_session.add(log)
        await test_session.flush()
        await handle_onec_apply_changes(test_session, {"log_id": log.id})
        await test_session.commit()

    await test_session.refresh(product)
    assert product.images == ["/uploads/onec/existing.jpg", "/uploads/onec/new.jpg"]

    # Неизвестный товар — молча пропускается
    payload = _build_payload(
        "product_images",
        [
            {
                "external_id": "1c-no-such-product",
                "action": "update",
                "version": datetime.now(timezone.utc).isoformat(),
                "data": {"images": ["/uploads/onec/x.jpg"]},
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="product_images",
        payload=payload,
        status="pending",
        checksum=f"checksum-imgs-{uuid4()}",
    )
    test_session.add(log)
    await test_session.flush()
    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()
    await test_session.refresh(log)
    assert log.status == "done"


@pytest.mark.asyncio
async def test_onec_apply_product_change_weight_and_deletion(test_session, supplier_id):
    """Товарный change: weight_grams и DeletionMark → is_active=false."""
    version = datetime.now(timezone.utc)
    payload = _build_payload(
        "product",
        [
            {
                "external_id": "1c-prod-del",
                "action": "update",
                "version": version.isoformat(),
                "data": {
                    "name": "Deleted Product",
                    "supplier_id": supplier_id,
                    "weight_grams": 250,
                    "is_active": False,
                },
            }
        ],
    )
    log = OnecChangeLog(
        batch_id=payload["batch_id"],
        entity_type="product",
        payload=payload,
        status="pending",
        checksum=f"checksum-prod-del-{uuid4()}",
    )
    test_session.add(log)
    await test_session.flush()
    await handle_onec_apply_changes(test_session, {"log_id": log.id})
    await test_session.commit()

    result = await test_session.execute(
        select(Product).where(Product.onec_id == "1c-prod-del")
    )
    product = result.scalar_one()
    assert product.weight_grams == 250
    assert product.is_active is False
