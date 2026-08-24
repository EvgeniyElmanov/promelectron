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
async def test_onec_apply_changes_rolls_back_batch_on_error(test_session, supplier_id):
    """A failed change inside a batch must rollback all changes and mark the log failed."""
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
                    "price": 99.99,
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
                    "price": 99.99,
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

    with pytest.raises(ValueError):
        await handle_onec_apply_changes(test_session, {"log_id": log.id})

    await test_session.commit()

    result = await test_session.execute(
        select(Product).where(Product.onec_id == "1c-prod-valid")
    )
    assert result.scalar_one_or_none() is None

    await test_session.refresh(log)
    assert log.status == "failed"
    assert log.error_message is not None
    assert "non-existent-onec-id" in log.error_message


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
    assert len(log_list) == 4  # category, product, price, stock

    jobs = await test_session.execute(select(Job).where(Job.job_type == "ONEC_APPLY_CHANGES"))
    job_list = jobs.scalars().all()
    assert len(job_list) == 4

    product_log = next(log for log in log_list if log.entity_type == "product")
    assert product_log.checksum is not None
    assert product_log.payload["changes"][0]["data"]["supplier_id"] == supplier_id
