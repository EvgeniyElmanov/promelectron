from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.models.favorite import Favorite
from src.app.models.product import Product
from src.app.models.user import User


class FavoriteService:
    @staticmethod
    async def add_to_favorites(product_id: int, current_user: User, db: AsyncSession) -> Favorite:
        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        existing = await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id, Favorite.product_id == product_id
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Product already in favorites")

        favorite = Favorite(user_id=current_user.id, product_id=product_id)
        db.add(favorite)
        await db.commit()
        await db.refresh(favorite)
        return favorite

    @staticmethod
    async def remove_from_favorites(product_id: int, current_user: User, db: AsyncSession) -> dict[str, str]:
        result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id, Favorite.product_id == product_id
            )
        )
        favorite = result.scalars().first()
        if not favorite:
            raise HTTPException(status_code=404, detail="Favorite not found")

        await db.delete(favorite)
        await db.commit()
        return {"message": "Product removed from favorites"}

    @staticmethod
    async def get_favorites(current_user: User, db: AsyncSession) -> list[Favorite]:
        result = await db.execute(
            select(Favorite)
            .where(Favorite.user_id == current_user.id)
            .options(selectinload(Favorite.product))
        )
        return list(result.scalars().all())

    @staticmethod
    async def is_favorite(product_id: int, current_user: User, db: AsyncSession) -> bool:
        result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id, Favorite.product_id == product_id
            )
        )
        return result.scalars().first() is not None
