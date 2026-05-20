from __future__ import annotations

import logging

from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)


async def update_price_timer(ozon: OzonClient) -> None:
    logger.info("Starting price timer update: fetching product IDs")

    product_ids: list[int] = []
    async for page in await ozon.get_products_list():
        for item in page:
            pid = item.get("product_id")
            if pid:
                product_ids.append(int(pid))

    if not product_ids:
        logger.info("No products found, skipping price timer update")
        return

    logger.info("Updating price timer for %d products", len(product_ids))
    await ozon.update_price_timer(product_ids)
    logger.info("Price timer update complete: %d products processed", len(product_ids))
