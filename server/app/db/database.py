from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from server.app.core.config import settings

DATABASE_URL = settings.database_url

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
async_session_maker = SessionLocal


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session

