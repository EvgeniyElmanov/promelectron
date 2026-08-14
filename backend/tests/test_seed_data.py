"""Regression test: /api/v1/seed падал с 500 MultipleResultsFound, когда
категории/товары с демо-именами уже существуют в двух копиях (демо-seed +
1C-intake, матч intake только по onec_id). Lookup'и seed по не-unique
Category.name / Product.name должны быть толерантны к дублям
(run 31790205986)."""

import pytest
from sqlalchemy import select

from seed_data import (
    TEST_CATEGORIES,
    TEST_PRODUCTS,
    create_products,
    get_or_create_categories,
)
from src.app.models.category import Category
from src.app.models.product import Product
from src.app.models.supplier import Supplier
from src.app.models.user import RoleEnum, User


async def _make_supplier(session) -> Supplier:
    user = User(
        email="seed-test-supplier@example.com",
        hashed_password="x",
        role=RoleEnum.supplier,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    supplier = Supplier(
        user_id=user.id,
        name="Seed Test Supplier",
        api_key="seed-test-api-key",
        is_active=True,
    )
    session.add(supplier)
    await session.flush()
    return supplier


@pytest.mark.asyncio
async def test_get_or_create_categories_tolerates_duplicate_names(test_session):
    """Две категории с одинаковым именем (дубль от 1C-intake) не роняют seed."""
    name = TEST_CATEGORIES[0]["name"]
    dup1 = Category(name=name, description="demo")
    dup2 = Category(name=name, description="1c")
    test_session.add_all([dup1, dup2])
    await test_session.commit()

    categories_map = await get_or_create_categories(test_session)

    assert len(categories_map) == len(TEST_CATEGORIES)
    reused = categories_map[name]
    # Переиспользована одна из существующих категорий, новая не создана
    assert reused.id in {dup1.id, dup2.id}


@pytest.mark.asyncio
async def test_create_products_tolerates_duplicate_names(test_session):
    """Два товара с одинаковым именем не роняют seed, товар пропускается."""
    supplier = await _make_supplier(test_session)
    categories_map = await get_or_create_categories(test_session)

    payload = TEST_PRODUCTS[0]
    category = categories_map[payload["category_name"]]
    for _ in range(2):
        test_session.add(
            Product(
                name=payload["name"],
                description="duplicate",
                price=1.0,
                stock=1,
                category_id=category.id,
                supplier_id=supplier.id,
                is_active=True,
            )
        )
    await test_session.commit()

    await create_products(test_session, supplier, categories_map)
    await test_session.commit()

    result = await test_session.execute(
        select(Product).where(Product.name == payload["name"])
    )
    # Дублированный товар пропущен: остались ровно две исходные копии
    assert len(result.scalars().all()) == 2
