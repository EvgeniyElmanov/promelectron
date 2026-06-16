from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.category import Category
from src.app.models.product import Product
from src.app.schemas.category import CategoryCreate


class CategoryService:
    @staticmethod
    async def _product_count_for(category_id: int, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        )
        return result.scalar() or 0

    @staticmethod
    async def _descendant_ids(category_id: int, db: AsyncSession) -> set[int]:
        descendants: set[int] = set()
        current_level = {category_id}
        while current_level:
            result = await db.execute(
                select(Category.id).where(Category.parent_id.in_(current_level))
            )
            current_level = set(result.scalars().all()) - descendants
            descendants.update(current_level)
        return descendants

    @staticmethod
    async def _reject_cycle(
        category_id: int, new_parent_id: int | None, db: AsyncSession
    ) -> None:
        if new_parent_id is None:
            return
        if new_parent_id == category_id:
            raise HTTPException(
                status_code=400, detail="Cannot set category as its own parent"
            )
        descendants = await CategoryService._descendant_ids(category_id, db)
        if new_parent_id in descendants:
            raise HTTPException(
                status_code=400, detail="Cannot set a descendant as parent"
            )

    @staticmethod
    async def create_category(
        category_data: CategoryCreate, db: AsyncSession
    ) -> Category:
        if category_data.parent_id is not None:
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
        new_category.product_count = 0
        return new_category

    @staticmethod
    async def get_category(category_id: int, db: AsyncSession) -> Category:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        category.product_count = await CategoryService._product_count_for(
            category.id, db
        )
        return category

    @staticmethod
    async def list_categories(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        parent_id: int | None = None,
        q: str | None = None,
    ) -> tuple[list[Category], int]:
        filters = []
        if parent_id is not None:
            filters.append(Category.parent_id == parent_id)
        if q:
            filters.append(Category.name.ilike(f"%{q}%"))

        whereclause = None
        if len(filters) == 1:
            whereclause = filters[0]
        elif filters:
            whereclause = and_(*filters)

        count_stmt = select(func.count(Category.id)).select_from(Category)
        if whereclause is not None:
            count_stmt = count_stmt.where(whereclause)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(Category, func.count(Product.id).label("product_count"))
            .outerjoin(Product, Product.category_id == Category.id)
            .group_by(Category.id)
        )
        if whereclause is not None:
            stmt = stmt.where(whereclause)
        stmt = stmt.order_by(Category.id).offset(skip).limit(limit)

        result = await db.execute(stmt)
        items: list[Category] = []
        for category, product_count in result.all():
            category.product_count = product_count or 0
            items.append(category)

        return items, total

    @staticmethod
    async def update_category(
        category_id: int, category_data: CategoryCreate, db: AsyncSession
    ) -> Category:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        await CategoryService._reject_cycle(category.id, category_data.parent_id, db)

        if category_data.parent_id is not None:
            parent_result = await db.execute(
                select(Category).where(Category.id == category_data.parent_id)
            )
            parent = parent_result.scalars().first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")

        for field, value in category_data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)

        await db.commit()
        await db.refresh(category)
        category.product_count = await CategoryService._product_count_for(
            category.id, db
        )
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
