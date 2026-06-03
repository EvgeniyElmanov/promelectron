from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from collector.clickhouse_client import ClickHouseClient
from collector.config import Settings
from collector.ozon_client import OzonClient
from collector.sync.analytics import sync_analytics
from collector.sync.categories import sync_categories
from collector.sync.orders import sync_orders
from collector.sync.price_timer import update_price_timer
from collector.sync.prices import sync_prices
from collector.sync.product_queries import sync_product_queries
from collector.sync.products import sync_products
from collector.sync.stocks import sync_stocks
from collector.sync.transactions import sync_transactions

logger = logging.getLogger("collector")

VALID_ENTITIES = {"products", "orders", "transactions", "stocks", "prices", "analytics", "product_queries", "categories"}


def _parse_cron(expr: str) -> dict[str, str]:
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Expected 5-field cron expression, got {len(parts)} fields: {expr!r}"
        )
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


async def run_sync(
    settings: Settings,
    *,
    full: bool = False,
    since: str | None = None,
    entities: set[str] | None = None,
) -> None:
    do_all = entities is None
    mode = "FULL" if full else "INCREMENTAL"
    logger.info("Starting %s sync (entities: %s)", mode, entities or "all")

    ch = ClickHouseClient(settings)
    ch.open()
    try:
        async with OzonClient(settings) as ozon:
            # Fast syncs first (seconds)
            if do_all or "categories" in entities:
                await sync_categories(ozon, ch)

            if do_all or "products" in entities:
                await sync_products(ozon, ch)

            if do_all or "stocks" in entities:
                await sync_stocks(ozon, ch)

            if do_all or "prices" in entities:
                await sync_prices(ozon, ch)

            # Medium syncs (minutes)
            if do_all or "orders" in entities:
                await sync_orders(ozon, ch, since=since, full=full)

            if do_all or "transactions" in entities:
                await sync_transactions(ozon, ch, since=since, full=full)

            if do_all or "product_queries" in entities:
                await sync_product_queries(ozon, ch)

            # Slow syncs last (analytics = 1 req/min, ~80 min for full)
            if do_all or "analytics" in entities:
                await sync_analytics(ozon, ch, since=since, full=full)
    except Exception:
        logger.exception("Error during %s sync", mode)
    finally:
        ch.close()

    logger.info("%s sync completed", mode)


def _make_sync_job(settings: Settings, entities: set[str]) -> Any:
    async def job() -> None:
        await run_sync(settings, full=False, entities=entities)

    return job


def _make_price_timer_job(settings: Settings) -> Any:
    async def job() -> None:
        logger.info("Running scheduled price timer update")
        try:
            async with OzonClient(settings) as ozon:
                await update_price_timer(ozon)
        except Exception:
            logger.exception("Error during price timer update")

    return job


async def _run_service(
    settings: Settings,
    *,
    full_sync: bool = False,
    since: str | None = None,
    entities: set[str] | None = None,
) -> None:
    ch = ClickHouseClient(settings)
    ch.open()
    try:
        ch.run_migrations()
    finally:
        ch.close()

    if full_sync:
        logger.info("--full-sync detected, running immediate sync")
        await run_sync(settings, full=True, since=since, entities=entities)

    scheduler = AsyncIOScheduler()

    # Products: every 4 hours
    scheduler.add_job(
        _make_sync_job(settings, {"products"}),
        trigger=CronTrigger(**_parse_cron(settings.products_cron)),
        id="products_sync",
        name="Products sync",
        misfire_grace_time=600,
    )

    # Orders: every 30 minutes
    scheduler.add_job(
        _make_sync_job(settings, {"orders"}),
        trigger=CronTrigger(**_parse_cron(settings.orders_cron)),
        id="orders_sync",
        name="Orders sync",
        misfire_grace_time=300,
    )

    # Transactions: daily at 03:00
    scheduler.add_job(
        _make_sync_job(settings, {"transactions"}),
        trigger=CronTrigger(**_parse_cron(settings.transactions_cron)),
        id="transactions_sync",
        name="Transactions sync",
        misfire_grace_time=600,
    )

    # Stocks snapshot: every 4 hours
    scheduler.add_job(
        _make_sync_job(settings, {"stocks"}),
        trigger=CronTrigger(**_parse_cron(settings.stocks_cron)),
        id="stocks_sync",
        name="Stocks snapshot",
        misfire_grace_time=600,
    )

    # Prices: every 4 hours
    scheduler.add_job(
        _make_sync_job(settings, {"prices"}),
        trigger=CronTrigger(**_parse_cron(settings.prices_cron)),
        id="prices_sync",
        name="Prices sync",
        misfire_grace_time=600,
    )

    # Analytics (revenue/ordered_units per SKU/day): daily at 04:00
    scheduler.add_job(
        _make_sync_job(settings, {"analytics"}),
        trigger=CronTrigger(**_parse_cron(settings.analytics_cron)),
        id="analytics_sync",
        name="Analytics sync",
        misfire_grace_time=600,
    )

    # Product queries (search queries per SKU): daily at 05:00
    scheduler.add_job(
        _make_sync_job(settings, {"product_queries"}),
        trigger=CronTrigger(**_parse_cron(settings.product_queries_cron)),
        id="product_queries_sync",
        name="Product queries sync",
        misfire_grace_time=600,
    )

    # Categories: daily at 02:00
    scheduler.add_job(
        _make_sync_job(settings, {"categories"}),
        trigger=CronTrigger(**_parse_cron(settings.categories_cron)),
        id="categories_sync",
        name="Categories sync",
        misfire_grace_time=600,
    )

    # Price timer update: every N days (default 25)
    scheduler.add_job(
        _make_price_timer_job(settings),
        trigger=IntervalTrigger(days=settings.price_timer_interval_days),
        id="price_timer_update",
        name="Price timer update",
        misfire_grace_time=86400,
    )

    scheduler.start()
    logger.info(
        "Scheduler started. Products: %s | Orders: %s | Transactions: %s | "
        "Stocks: %s | Prices: %s | Analytics: %s | ProductQueries: %s | "
        "Categories: %s | PriceTimer: every %d days",
        settings.products_cron,
        settings.orders_cron,
        settings.transactions_cron,
        settings.stocks_cron,
        settings.prices_cron,
        settings.analytics_cron,
        settings.product_queries_cron,
        settings.categories_cron,
        settings.price_timer_interval_days,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()
    scheduler.shutdown(wait=True)
    logger.info("Collector service stopped")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promelectron collector service")
    parser.add_argument(
        "--full-sync",
        action="store_true",
        default=False,
        help="Run full sync on startup before starting the scheduler",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Start date for sync (YYYY-MM-DD). Only used with --full-sync",
    )
    parser.add_argument(
        "--entities",
        type=str,
        default=None,
        help=(
            "Comma-separated entity types to sync: "
            "products,orders,transactions,stocks,analytics. "
            "Default: all"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    settings = Settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    entities = None
    if args.entities:
        entities = {e.strip() for e in args.entities.split(",") if e.strip()}
        unknown = entities - VALID_ENTITIES
        if unknown:
            logger.error("Unknown entity types: %s (valid: %s)", unknown, VALID_ENTITIES)
            sys.exit(1)

    asyncio.run(
        _run_service(
            settings,
            full_sync=args.full_sync,
            since=args.since,
            entities=entities,
        )
    )


if __name__ == "__main__":
    main()
