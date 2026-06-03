from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from collector.clickhouse_client import ClickHouseClient
from collector.ozon_client import OzonClient

logger = logging.getLogger(__name__)

_CATEGORIES_COLUMNS = [
    "category_id",
    "category_name",
    "parent_id",
    "level",
    "type_id",
    "type_name",
]

_SYNC_KEY = "global"
_ENTITY_TYPE = "categories"


def _flatten_tree(
    nodes: list[dict[str, Any]],
    parent_id: int = 0,
    level: int = 0,
) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for node in nodes:
        children: list[dict[str, Any]] = node.get("children", []) or []

        if "description_category_id" in node:
            # Intermediate category node
            category_id = int(node["description_category_id"])
            category_name = str(node.get("category_name", "") or "")
            rows.append((
                category_id,
                category_name,
                parent_id,
                level,
                0,
                "",
            ))
            if children:
                rows.extend(
                    _flatten_tree(children, parent_id=category_id, level=level + 1)
                )
        elif "type_id" in node:
            # Leaf type node — use parent_id as category_id, type_id as own id
            type_id = int(node["type_id"])
            type_name = str(node.get("type_name", "") or "")
            rows.append((
                type_id,
                type_name,
                parent_id,
                level,
                type_id,
                type_name,
            ))

    return rows


async def sync_categories(ozon: OzonClient, ch: ClickHouseClient) -> None:
    logger.info("Starting categories sync")

    data = await ozon.get_category_tree()
    tree: list[dict[str, Any]] = data.get("result", []) or []

    if not tree:
        logger.warning("Category tree is empty, skipping sync")
        return

    rows = _flatten_tree(tree)
    logger.info("Flattened %d category/type nodes", len(rows))

    ch.insert_rows("categories", _CATEGORIES_COLUMNS, rows)
    ch.optimize_table("categories")

    now = datetime.now(UTC)
    ch.save_checkpoint(_SYNC_KEY, _ENTITY_TYPE, now, len(rows))

    logger.info("Categories sync complete: %d rows inserted", len(rows))
