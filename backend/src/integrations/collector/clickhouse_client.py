from __future__ import annotations

import logging
import pathlib
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver import Client

from collector.config import Settings

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "migrations"

_SQL_SPLIT_RE = re.compile(
    r"""'(?:[^']|'')*'"""    # single-quoted string literal (skip)
    r"""|--[^\n]*"""         # single-line comment (skip)
    r"""|/\*[\s\S]*?\*/"""   # block comment (skip)
    r"""|(;)""",             # capturing group: actual statement delimiter
    re.DOTALL,
)

# Safety guard: optimize_table() uses f-string interpolation for the table name
_ALLOWED_TABLES = frozenset({
    "products",
    "orders",
    "transactions",
    "prices",
    "stocks",
    "analytics_sales",
    "product_queries",
    "categories",
    "sync_checkpoints",
})


def _split_sql_statements(sql: str) -> list[str]:
    parts: list[str] = []
    last = 0
    for m in _SQL_SPLIT_RE.finditer(sql):
        if m.group(1) is not None:
            parts.append(sql[last:m.start()])
            last = m.end()
    parts.append(sql[last:])
    return [s.strip() for s in parts if s.strip()]


class ClickHouseClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Client | None = None

    def open(self) -> None:
        bootstrap = clickhouse_connect.get_client(
            host=self._settings.clickhouse_host,
            port=self._settings.clickhouse_port,
            username=self._settings.clickhouse_user,
            password=self._settings.clickhouse_password.get_secret_value(),
        )
        bootstrap.command(
            f"CREATE DATABASE IF NOT EXISTS {self._settings.clickhouse_database}"
        )
        bootstrap.close()

        self._client = clickhouse_connect.get_client(
            host=self._settings.clickhouse_host,
            port=self._settings.clickhouse_port,
            username=self._settings.clickhouse_user,
            password=self._settings.clickhouse_password.get_secret_value(),
            database=self._settings.clickhouse_database,
        )
        logger.info(
            "Connected to ClickHouse at %s:%s/%s",
            self._settings.clickhouse_host,
            self._settings.clickhouse_port,
            self._settings.clickhouse_database,
        )

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> ClickHouseClient:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def client(self) -> Client:
        if self._client is None:
            raise RuntimeError(
                "ClickHouse client is not open — call open() or use as context manager"
            )
        return self._client

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------

    def _ensure_migrations_table(self) -> None:
        self.client.command(
            "CREATE TABLE IF NOT EXISTS _migrations "
            "(filename String, applied_at DateTime DEFAULT now()) "
            "ENGINE = MergeTree ORDER BY filename"
        )

    def _get_applied_migrations(self) -> set[str]:
        result = self.client.query("SELECT filename FROM _migrations")
        return {row[0] for row in result.result_rows}

    def run_migrations(self) -> None:
        self._ensure_migrations_table()
        applied = self._get_applied_migrations()
        migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
        newly_applied = 0
        for fpath in migration_files:
            if fpath.name in applied:
                logger.debug("Skipping already applied migration: %s", fpath.name)
                continue
            logger.info("Running migration: %s", fpath.name)
            sql = fpath.read_text(encoding="utf-8")
            for stmt in _split_sql_statements(sql):
                self.client.command(stmt)
            self.client.command(
                "INSERT INTO _migrations (filename) VALUES ({fn:String})",
                parameters={"fn": fpath.name},
            )
            newly_applied += 1
        logger.info(
            "Migrations complete: %d applied, %d skipped",
            newly_applied,
            len(migration_files) - newly_applied,
        )

    # ------------------------------------------------------------------
    # Generic insert helpers
    # ------------------------------------------------------------------

    def insert_rows(
        self,
        table: str,
        column_names: list[str],
        rows: Sequence[Sequence[Any]],
    ) -> None:
        if not rows:
            return
        batch_size = self._settings.clickhouse_batch_size
        total = len(rows)
        for offset in range(0, total, batch_size):
            batch = rows[offset : offset + batch_size]
            self.client.insert(table, data=batch, column_names=column_names)
            logger.debug(
                "Inserted batch %d-%d/%d into %s",
                offset,
                min(offset + batch_size, total),
                total,
                table,
            )

    def optimize_table(self, table: str) -> None:
        if table not in _ALLOWED_TABLES:
            raise ValueError(f"optimize_table called with unknown table: {table!r}")
        self.client.command(f"OPTIMIZE TABLE {table} FINAL")
        logger.debug("OPTIMIZE TABLE %s FINAL completed", table)

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def get_checkpoint(self, sync_key: str, entity_type: str) -> datetime | None:
        result = self.client.query(
            "SELECT last_synced_at FROM sync_checkpoints FINAL "
            "WHERE sync_key = {sk:String} AND entity_type = {et:String} "
            "ORDER BY synced_at DESC "
            "LIMIT 1",
            parameters={"sk": sync_key, "et": entity_type},
        )
        if result.result_rows:
            val = result.result_rows[0][0]
            if isinstance(val, datetime):
                return val.replace(tzinfo=UTC) if val.tzinfo is None else val
        return None

    def save_checkpoint(
        self,
        sync_key: str,
        entity_type: str,
        last_synced_at: datetime,
        items_synced: int,
    ) -> None:
        now = datetime.now(UTC)
        self.insert_rows(
            "sync_checkpoints",
            ["sync_key", "entity_type", "last_synced_at", "synced_at", "items_synced"],
            [(sync_key, entity_type, last_synced_at, now, items_synced)],
        )
