from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.models.category import Category
from server.app.schemas.category import CategoryCreate


class CategoryService:
    @staticmethod
    async def create_category(category_data: CategoryCreate, db: AsyncSession) -> Category:
        if category_data.parent_id:
            parent_result = await db.execute(
                select(Category).where(Category.id == category_data.parent_id)
            )
            parent = parent_result.scalars().first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")

        new_category = Category(**category_data.model_dump())
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        return new_category

    @staticmethod
    async def get_category(category_id: int, db: AsyncSession) -> Category:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[Category]:
        result = await db.execute(select(Category))
        return list(result.scalars().all())
