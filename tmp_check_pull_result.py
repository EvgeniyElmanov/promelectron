import asyncio
import os

os.environ.setdefault("ENVIRONMENT", "test")

from sqlalchemy import select, text
from src.app.db.database import SessionLocal
from src.app.models.onec_sync import OnecChangeLog
from src.app.models.category import Category
from src.app.models.product import Product

async def main():
    async with SessionLocal() as session:
        print("=== onec_change_log (last 10) ===")
        result = await session.execute(
            select(OnecChangeLog).order_by(OnecChangeLog.id.desc()).limit(10)
        )
        for log in result.scalars():
            print(f"id={log.id} entity={log.entity_type!s:<8} status={log.status!s:<10} source={log.source} batch={log.batch_id}")

        print("\n=== categories ===")
        result = await session.execute(select(Category).order_by(Category.id.desc()).limit(10))
        for c in result.scalars():
            print(f"id={c.id} name={c.name!s:<20} onec_id={c.onec_id} parent={c.parent_id} active={c.is_active}")

        print("\n=== products (created from 1C pull) ===")
        result = await session.execute(
            select(Product).where(Product.onec_id.like("%aaaa%") | Product.onec_id.like("%cccc%")).order_by(Product.id.desc())
        )
        for p in result.scalars():
            print(f"id={p.id} name={p.name!s:<25} sku={p.sku} price={p.price} stock={p.stock} onec_id={p.onec_id} category={p.category_id} active={p.is_active}")

asyncio.run(main())
