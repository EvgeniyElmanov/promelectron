"""Тесты проверки соответствия схемы БД ревизиям Alembic на старте (gh-217).

Схема в тестовой БД строится через ``Base.metadata.create_all`` (conftest),
таблица ``alembic_version`` в ней отсутствует — негативный кейс «нет таблицы»
получается без дополнительной подготовки.
"""

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from src.app.main import _alembic_cfg_path, _check_schema_version


def _expected_heads() -> list[str]:
    cfg = Config(_alembic_cfg_path())
    return list(ScriptDirectory.from_config(cfg).get_heads())


async def _create_alembic_version(engine, revisions: list[str]) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        for rev in revisions:
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
                {"rev": rev},
            )


async def test_check_schema_version_ok_on_current_head(test_engine):
    """alembic_version содержит текущий head → проверка проходит."""
    await _create_alembic_version(test_engine, _expected_heads())
    await _check_schema_version(test_engine)


async def test_check_schema_version_missing_table_fails(test_engine):
    """Нет таблицы alembic_version → RuntimeError (миграции не применялись)."""
    with pytest.raises(RuntimeError, match="alembic_version"):
        await _check_schema_version(test_engine)


async def test_check_schema_version_stale_revision_fails(test_engine):
    """Применена неизвестная/старая ревизия → RuntimeError."""
    await _create_alembic_version(test_engine, ["0000_stale_rev"])
    with pytest.raises(RuntimeError, match="schema mismatch"):
        await _check_schema_version(test_engine)
