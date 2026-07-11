from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.app.models.category import Category
from src.app.models.onec_sync import OnecChangeLog
from src.app.models.product import Product
from src.app.models.supplier import Supplier
from src.app.services.onec_sync_service import handle_onec_apply_changes


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
    assert product.price == 299.99
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

    delete_payload = _build_payload(
        "category",
        [
            {
                "external_id": "1c-cat-300",
                "action": "delete",
                "version": version.isoformat(),
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
