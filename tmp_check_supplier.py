import asyncio
import os
os.environ.setdefault("ENVIRONMENT", "test")

from src.app.db.database import SessionLocal
from src.app.models.supplier import Supplier
from sqlalchemy import select

async def main():
    async with SessionLocal() as session:
        result = await session.execute(select(Supplier).limit(10))
        for s in result.scalars():
            print(s.id, s.name)

asyncio.run(main())
