"""Тесты сценариев мутаций (D-06)."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from onec_mock.config import settings
from onec_mock.models import ChangeLog, Product
from onec_mock.scenarios import run_scenario
from onec_mock.seed import seed_catalog


async def test_new_products_adds_products_and_changes(seeded_session):
    before = await seeded_session.scalar(select(func.count(Product.id)))
    # D-03: seed-записи change_log не считаем — только изменения сценария
    max_change_id = await seeded_session.scalar(select(func.max(ChangeLog.id))) or 0

    run = await run_scenario(seeded_session, settings, "new_products", {"count": 5})

    after = await seeded_session.scalar(select(func.count(Product.id)))
    assert after == before + 5
    # на каждый товар: product create + price + stock
    assert run.changes_created == 15
    creates = await seeded_session.scalar(
        select(func.count(ChangeLog.id)).where(
            ChangeLog.id > max_change_id,
            ChangeLog.entity_type == "product", ChangeLog.action == "create"
        )
    )
    assert creates == 5
    assert run.status == "success"


async def test_mass_price_update_rounds_half_up(seeded_session):
    run = await run_scenario(seeded_session, settings, "mass_price_update", {"pct": 10})

    active = await seeded_session.scalar(
        select(func.count(Product.id)).where(Product.is_active.is_(True))
    )
    assert run.changes_created == active
    prices = (await seeded_session.execute(select(Product.price))).scalars()
    for price in prices:
        assert Decimal(str(price)).as_integer_ratio()[1] in (1, 2, 4, 5, 10, 20, 25, 50, 100)
        # эквивалентно: не более 2 знаков после запятой
        assert abs(float(price) * 100 - round(float(price) * 100)) < 1e-6


async def test_stock_out_never_negative(seeded_session):
    max_change_id = await seeded_session.scalar(select(func.max(ChangeLog.id))) or 0

    run = await run_scenario(seeded_session, settings, "stock_out", {"share": 0.5})

    negative = await seeded_session.scalar(
        select(func.count(Product.id)).where(Product.stock < 0)
    )
    assert negative == 0
    assert run.changes_created > 0
    zeroed = await seeded_session.scalar(
        select(func.count(ChangeLog.id)).where(
            ChangeLog.id > max_change_id,  # seed stock-create с new=0 не считаем (D-03)
            ChangeLog.entity_type == "stock",
            ChangeLog.payload["new"].as_integer() == 0,
        )
    )
    assert zeroed == run.changes_created


async def test_delete_products_marks_inactive(seeded_session):
    run = await run_scenario(seeded_session, settings, "delete_products", {"count": 3})

    inactive = await seeded_session.scalar(
        select(func.count(Product.id)).where(Product.is_active.is_(False))
    )
    assert inactive == 3
    deletes = await seeded_session.scalar(
        select(func.count(ChangeLog.id)).where(
            ChangeLog.entity_type == "product", ChangeLog.action == "delete"
        )
    )
    assert deletes == 3
    assert run.changes_created == 3


async def test_normal_scenario_creates_price_and_stock_changes(seeded_session):
    max_change_id = await seeded_session.scalar(select(func.max(ChangeLog.id))) or 0

    run = await run_scenario(seeded_session, settings, "normal", {})

    types = (
        await seeded_session.execute(
            select(ChangeLog.entity_type).distinct().where(ChangeLog.id > max_change_id)
        )
    ).scalars()
    assert set(types) <= {"price", "stock"}
    assert run.changes_created >= 2
    non_negative = await seeded_session.scalar(
        select(func.count(Product.id)).where(Product.stock < 0)
    )
    assert non_negative == 0


async def test_scenarios_are_deterministic_by_seed(session):
    """Одинаковое начальное состояние + seed → одинаковые мутации."""

    async def snapshot():
        await seed_catalog(session, settings)
        await run_scenario(session, settings, "normal", {})
        rows = (
            await session.execute(
                select(Product.onec_id, Product.price, Product.stock).order_by(Product.onec_id)
            )
        ).all()
        return [(r[0], str(r[1]), r[2]) for r in rows]

    first = await snapshot()
    # сброс каталога и повтор с тем же seed
    from sqlalchemy import delete

    from onec_mock.models import Attribute, Category, ProductAttributeValue, ScenarioRun

    for model in (ChangeLog, ProductAttributeValue, ScenarioRun, Product, Attribute, Category):
        await session.execute(delete(model))
    await session.commit()
    second = await snapshot()
    assert first == second


async def test_unknown_scenario_raises(seeded_session):
    with pytest.raises(ValueError, match="unknown scenario"):
        await run_scenario(seeded_session, settings, "no_such_scenario", {})
