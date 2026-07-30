"""Async engine/session по DATABASE_URL (D-03)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from onec_mock.config import settings

# NullPool: безопасно для pytest (новый event loop на тест) и достаточно для мока
engine = create_async_engine(settings.database_url, poolclass=NullPool, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Создать схему и таблицы onec_mock (без Alembic, D-03)."""
    from sqlalchemy import text

    from onec_mock.models import Base

    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.onec_mock_schema}"'))
        await conn.run_sync(Base.metadata.create_all)
