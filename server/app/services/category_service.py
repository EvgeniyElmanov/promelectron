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

    @staticmethod
    async def update_category(category_id: int, category_data: CategoryCreate, db: AsyncSession) -> Category:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        if category_data.parent_id and category_data.parent_id != category_id:
            parent_result = await db.execute(
                select(Category).where(Category.id == category_data.parent_id)
            )
            parent = parent_result.scalars().first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")

        for field, value in category_data.model_dump().items():
            setattr(category, field, value)

        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete_category(category_id: int, db: AsyncSession) -> dict[str, str]:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        await db.delete(category)
        await db.commit()
        return {"message": "Category deleted successfully"}
