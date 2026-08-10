"""Тесты seed'а электрокаталога (D-03/D-04).

Проверяют: change_log по 3 записи на товар, no-op на непустом каталоге,
детерминизм по CATALOG_SEED, структуру категорий, формат SKU/цен и заполнение
атрибута brand (нужен для фасетов, D-09).
"""

import re

from sqlalchemy import delete, func, select

from onec_mock.config import settings
from onec_mock.models import (
    Attribute,
    Category,
    ChangeLog,
    Product,
    ProductAttributeValue,
)
from onec_mock.seed import BRANDS, CHILD_CATEGORIES, ROOT_CATEGORIES, seed_catalog

LEAF_NAMES = [name for children in CHILD_CATEGORIES.values() for name in children]


async def test_seed_creates_products_and_pending_change_log(seeded_session):
    count = settings.seed_products_count

    products = await seeded_session.scalar(select(func.count(Product.id)))
    assert products == count

    pending = await seeded_session.scalar(
        select(func.count(ChangeLog.id)).where(ChangeLog.batch_id.is_(None))
    )
    assert pending == 3 * count

    # ровно по одной create-записи product/price/stock на каждый товар
    rows = (
        await seeded_session.execute(
            select(ChangeLog.entity_type, func.count())
            .where(ChangeLog.action == "create")
            .group_by(ChangeLog.entity_type)
        )
    ).all()
    assert dict(rows) == {"product": count, "price": count, "stock": count}


async def test_seed_is_noop_on_non_empty_catalog(seeded_session):
    before_products = await seeded_session.scalar(select(func.count(Product.id)))
    before_changes = await seeded_session.scalar(select(func.count(ChangeLog.id)))

    result = await seed_catalog(seeded_session, settings)

    assert result == 0
    assert await seeded_session.scalar(select(func.count(Product.id))) == before_products
    assert await seeded_session.scalar(select(func.count(ChangeLog.id))) == before_changes


async def test_seed_is_deterministic_by_catalog_seed(session):
    async def snapshot() -> list[tuple]:
        await seed_catalog(session, settings)
        rows = (
            await session.execute(
                select(Product.onec_id, Product.sku, Product.name, Product.price, Product.stock)
                .order_by(Product.sku)
            )
        ).all()
        return [(r[0], r[1], r[2], str(r[3]), r[4]) for r in rows]

    first = await snapshot()
    for model in (ChangeLog, ProductAttributeValue, Product, Attribute, Category):
        await session.execute(delete(model))
    await session.commit()
    second = await snapshot()
    assert first == second


async def test_seed_electro_catalog_shape(seeded_session):
    products = list((await seeded_session.execute(select(Product))).scalars())
    assert len(products) == settings.seed_products_count
    for product in products:
        assert re.fullmatch(r"EL-\d{5}", product.sku)
        assert 50 <= float(product.price) <= 15000
        assert product.name  # непустое реалистичное имя

    # round-robin: все листовые категории покрыты товарами (count == числу листовых)
    leaf_ids = dict(
        (
            await seeded_session.execute(
                select(Category.name, Category.onec_id).where(
                    Category.parent_onec_id.isnot(None)
                )
            )
        ).all()
    )
    assert set(leaf_ids) == set(LEAF_NAMES)
    if settings.seed_products_count >= len(LEAF_NAMES):
        used = {product.category_onec_id for product in products}
        assert set(leaf_ids.values()) <= used


async def test_seed_category_structure(seeded_session):
    roots = list(
        (
            await seeded_session.execute(
                select(Category).where(Category.parent_onec_id.is_(None))
            )
        ).scalars()
    )
    assert {root.name for root in roots} == set(ROOT_CATEGORIES)

    children = list(
        (
            await seeded_session.execute(
                select(Category).where(Category.parent_onec_id.isnot(None))
            )
        ).scalars()
    )
    root_name_by_id = {root.onec_id: root.name for root in roots}
    children_by_root: dict[str, list[str]] = {}
    for child in children:
        children_by_root.setdefault(root_name_by_id[child.parent_onec_id], []).append(child.name)
    for root_name in ROOT_CATEGORIES:
        assert sorted(children_by_root[root_name]) == sorted(CHILD_CATEGORIES[root_name])


async def test_seed_brand_attribute_filled_for_all_products(seeded_session):
    brand_attr = await seeded_session.scalar(select(Attribute).where(Attribute.code == "brand"))
    assert brand_attr is not None
    products = list((await seeded_session.execute(select(Product))).scalars())
    for product in products:
        value = await seeded_session.scalar(
            select(ProductAttributeValue.value_text).where(
                ProductAttributeValue.product_id == product.id,
                ProductAttributeValue.attribute_id == brand_attr.id,
            )
        )
        assert value in BRANDS


async def test_seed_change_log_payload_format_matches_scenarios(seeded_session):
    """Payload seed-записей повторяет каноничный формат scenarios._log (D-03)."""
    product_change = await seeded_session.scalar(
        select(ChangeLog).where(ChangeLog.entity_type == "product").limit(1)
    )
    assert set(product_change.payload) == {"name", "sku"}

    price_change = await seeded_session.scalar(
        select(ChangeLog).where(ChangeLog.entity_type == "price").limit(1)
    )
    assert isinstance(price_change.payload["new"], str)

    stock_change = await seeded_session.scalar(
        select(ChangeLog).where(ChangeLog.entity_type == "stock").limit(1)
    )
    assert isinstance(stock_change.payload["new"], int)
