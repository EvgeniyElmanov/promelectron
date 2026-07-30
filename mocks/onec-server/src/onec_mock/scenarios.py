"""Реестр сценариев мутаций виртуального каталога (D-06).

Каждый сценарий детерминирован (rng по seed), пишет записи в change_log (D-04)
и фиксирует запуск в scenario_runs. Сценарии duplicate_batch и bad_checksum
не мутируют каталог — они модифицируют отправку и обрабатываются пайплайном
отправки (sender), здесь лишь регистрируются как special-сценарии.
"""

import logging
import random
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onec_mock.config import Settings
from onec_mock.models import (
    Attribute,
    Category,
    ChangeLog,
    Product,
    ProductAttributeValue,
    ScenarioRun,
)

logger = logging.getLogger("onec_mock.scenarios")


class Scenario(StrEnum):
    normal = "normal"
    new_products = "new_products"
    mass_price_update = "mass_price_update"
    stock_out = "stock_out"
    delete_products = "delete_products"
    duplicate_batch = "duplicate_batch"
    bad_checksum = "bad_checksum"


@dataclass
class ScenarioContext:
    session: AsyncSession
    settings: Settings
    rng: random.Random
    changes: list[ChangeLog]


def _q2(value: Decimal) -> Decimal:
    """Округление цены до 2 знаков ROUND_HALF_UP (инвариант B-01)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _log(ctx: ScenarioContext, entity_type: str, onec_id: str, action: str, payload: dict) -> None:
    change = ChangeLog(
        entity_type=entity_type, entity_onec_id=onec_id, action=action, payload=payload
    )
    ctx.session.add(change)
    ctx.changes.append(change)


async def _active_products(ctx: ScenarioContext) -> list[Product]:
    rows = await ctx.session.execute(select(Product).where(Product.is_active.is_(True)))
    return list(rows.scalars())


async def _scenario_normal(ctx: ScenarioContext, params: dict) -> None:
    """Небольшие правки цен/остатков у 5–10% товаров."""
    products = await _active_products(ctx)
    if not products:
        return
    share = ctx.rng.uniform(0.05, 0.10)
    selected = ctx.rng.sample(products, max(1, int(len(products) * share)))
    for product in selected:
        old_price = Decimal(str(product.price))
        factor = Decimal("1") + Decimal(str(ctx.rng.uniform(-0.05, 0.05)))
        new_price = _q2(old_price * factor)
        old_stock = product.stock
        delta = ctx.rng.randint(-10, 10)
        new_stock = max(0, old_stock + delta)  # инвариант B-02: stock >= 0
        product.price = new_price
        product.stock = new_stock
        product.updated_at = datetime.now(UTC)
        _log(ctx, "price", product.onec_id, "update",
             {"old": str(old_price), "new": str(new_price)})
        _log(ctx, "stock", product.onec_id, "update",
             {"old": old_stock, "new": new_stock})


async def _scenario_new_products(ctx: ScenarioContext, params: dict) -> None:
    """Добавить K новых товаров с GUID-ами и атрибутами."""
    count = int(params.get("count", 5))
    categories = list(
        (
            await ctx.session.execute(
                select(Category).where(
                    Category.is_active.is_(True), Category.parent_onec_id.isnot(None)
                )
            )
        ).scalars()
    )
    attributes = list((await ctx.session.execute(select(Attribute))).scalars())
    if not categories:
        raise ValueError("no leaf categories to attach new products")
    max_sku = await ctx.session.scalar(select(func.max(Product.sku))) or "SKU-00000"
    sku_counter = int(max_sku.split("-")[1]) + 1
    for _ in range(count):
        category = ctx.rng.choice(categories)
        product = Product(
            onec_id=str(uuid.UUID(int=ctx.rng.getrandbits(128))),
            sku=f"SKU-{sku_counter:05d}",
            name=f"{category.name} новинка {sku_counter}",
            description="Добавлен сценарием new_products",
            category_onec_id=category.onec_id,
            price=_q2(Decimal(str(ctx.rng.uniform(500, 150000)))),
            stock=ctx.rng.randint(0, 200),
        )
        ctx.session.add(product)
        await ctx.session.flush()
        sku_counter += 1
        for attr in ctx.rng.sample(attributes, k=min(len(attributes), ctx.rng.randint(2, 4))):
            if attr.value_type == "number":
                ctx.session.add(
                    ProductAttributeValue(
                        product_id=product.id,
                        attribute_id=attr.id,
                        value_number=Decimal(str(ctx.rng.uniform(1, 36))).quantize(Decimal("0.01")),
                    )
                )
            else:
                ctx.session.add(
                    ProductAttributeValue(
                        product_id=product.id, attribute_id=attr.id, value_text="new"
                    )
                )
        _log(ctx, "product", product.onec_id, "create", {"name": product.name, "sku": product.sku})
        _log(ctx, "price", product.onec_id, "create", {"new": str(product.price)})
        _log(ctx, "stock", product.onec_id, "create", {"new": product.stock})


async def _scenario_mass_price_update(ctx: ScenarioContext, params: dict) -> None:
    """Изменить цены всех активных товаров на ±pct%."""
    pct = Decimal(str(params.get("pct", 10))) / Decimal("100")
    for product in await _active_products(ctx):
        old_price = Decimal(str(product.price))
        sign = Decimal("1") if ctx.rng.random() < 0.5 else Decimal("-1")
        new_price = _q2(old_price * (Decimal("1") + sign * pct))
        product.price = new_price
        product.updated_at = datetime.now(UTC)
        _log(ctx, "price", product.onec_id, "update",
             {"old": str(old_price), "new": str(new_price)})


async def _scenario_stock_out(ctx: ScenarioContext, params: dict) -> None:
    """Обнулить остатки у доли товаров (инвариант B-02: stock >= 0)."""
    share = float(params.get("share", 0.2))
    products = await _active_products(ctx)
    selected = ctx.rng.sample(products, max(1, int(len(products) * share))) if products else []
    for product in selected:
        old_stock = product.stock
        product.stock = 0
        product.updated_at = datetime.now(UTC)
        _log(ctx, "stock", product.onec_id, "update", {"old": old_stock, "new": 0})


async def _scenario_delete_products(ctx: ScenarioContext, params: dict) -> None:
    """Пометить товары удалёнными."""
    count = int(params.get("count", 3))
    products = await _active_products(ctx)
    selected = ctx.rng.sample(products, min(count, len(products))) if products else []
    for product in selected:
        product.is_active = False
        product.updated_at = datetime.now(UTC)
        _log(ctx, "product", product.onec_id, "delete", {"name": product.name, "sku": product.sku})


async def _scenario_duplicate_batch(ctx: ScenarioContext, params: dict) -> None:
    """Повторная отправка последнего пакета — обрабатывается пайплайном отправки."""


async def _scenario_bad_checksum(ctx: ScenarioContext, params: dict) -> None:
    """Отправка с неверным X-1C-Checksum — обрабатывается пайплайном отправки."""


SPECIAL_SCENARIOS = {Scenario.duplicate_batch, Scenario.bad_checksum}

HANDLERS: dict[Scenario, Callable[[ScenarioContext, dict], Awaitable[None]]] = {
    Scenario.normal: _scenario_normal,
    Scenario.new_products: _scenario_new_products,
    Scenario.mass_price_update: _scenario_mass_price_update,
    Scenario.stock_out: _scenario_stock_out,
    Scenario.delete_products: _scenario_delete_products,
    Scenario.duplicate_batch: _scenario_duplicate_batch,
    Scenario.bad_checksum: _scenario_bad_checksum,
}


async def run_scenario(
    session: AsyncSession,
    settings: Settings,
    scenario: str,
    params: dict | None = None,
) -> ScenarioRun:
    """Запустить сценарий по имени, записать scenario_runs и change_log."""
    try:
        scenario_enum = Scenario(scenario)
    except ValueError as exc:
        raise ValueError(f"unknown scenario: {scenario}") from exc

    params = params or {}
    run = ScenarioRun(scenario=scenario_enum.value, params=params)
    session.add(run)
    await session.flush()

    runs_count = await session.scalar(select(func.count(ScenarioRun.id))) or 0
    rng = random.Random(f"{settings.catalog_seed}:{scenario_enum.value}:{runs_count}")
    ctx = ScenarioContext(session=session, settings=settings, rng=rng, changes=[])

    try:
        await HANDLERS[scenario_enum](ctx, params)
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(UTC)
        await session.commit()
        raise

    run.changes_created = len(ctx.changes)
    run.status = "success"
    run.finished_at = datetime.now(UTC)
    await session.commit()
    logger.info(
        "scenario %s done: %s changes (run id=%s)", scenario, run.changes_created, run.id
    )
    return run
