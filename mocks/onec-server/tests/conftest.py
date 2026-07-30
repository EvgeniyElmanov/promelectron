"""Фикстуры pytest мок-сервера 1С.

Инвариант проекта: тесты только против PostgreSQL в Docker (никогда SQLite).
Используется та же БД, что у backend (postgres из backend/docker-compose.yml),
но отдельная схема onec_mock_test — DROP SCHEMA CASCADE до и после каждого
теста (изоляция, drop per test).
"""

import os

# env ДО импорта onec_mock.* (config читает env при импорте)
os.environ.setdefault("ONEC_MOCK_SCHEMA", "onec_mock_test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron"
)
os.environ.setdefault("SEED_PRODUCTS_COUNT", "10")

import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402

from onec_mock.config import settings  # noqa: E402
from onec_mock.db import async_session, engine, init_db  # noqa: E402
from onec_mock.seed import seed_catalog  # noqa: E402

TEST_SCHEMA = "onec_mock_test"


@pytest_asyncio.fixture
async def db():
    """Чистая схема onec_mock_test на каждый тест (drop + create_all)."""
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
    await init_db()
    yield
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))


@pytest_asyncio.fixture
async def session(db):
    async with async_session() as s:
        yield s


@pytest_asyncio.fixture
async def seeded_session(session):
    """Сессия с заполненным стартовым каталогом (SEED_PRODUCTS_COUNT=10)."""
    await seed_catalog(session, settings)
    return session
