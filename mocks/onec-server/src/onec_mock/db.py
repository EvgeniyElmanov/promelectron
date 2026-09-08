"""Async engine/session по DATABASE_URL (та же БД, что у backend; схема из ONEC_MOCK_SCHEMA)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from onec_mock.config import settings

# NullPool: безопасно для pytest (новый event loop на тест) и достаточно для мока
engine = create_async_engine(settings.database_url, poolclass=NullPool, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session
