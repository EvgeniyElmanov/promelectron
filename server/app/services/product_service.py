from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.models.category import Category
from server.app.models.product import Product
from server.app.models.supplier import Supplier
from server.app.models.user import User
from server.app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    @staticmethod
    async def read_products(skip: int, limit: int, db: AsyncSession) -> list[Product]:
        result = await db.execute(
            select(Product).where(Product.is_active == True).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_product(
        product_data: ProductCreate, current_user: User, db: AsyncSession
    ) -> Product:
        if product_data.category_id:
            category_result = await db.execute(
                select(Category).where(Category.id == product_data.category_id)
            )
            category = category_result.scalars().first()
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")

        supplier_result = await db.execute(
            select(Supplier).where(Supplier.user_id == current_user.id)
        )
        supplier = supplier_result.scalars().first()
        if not supplier:
            raise HTTPException(status_code=403, detail="You are not registered as a supplier")

        new_product = Product(**product_data.model_dump(), supplier_id=supplier.id)
        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)
        return new_product

    @staticmethod
    async def read_product(product_id: int, db: AsyncSession) -> Product:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalars().first()
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @staticmethod
    async def update_product(
        product_id: int, product_data: ProductUpdate, current_user: User, db: AsyncSession
    ) -> Product:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        supplier_result = await db.execute(
            select(Supplier).where(Supplier.user_id == current_user.id)
        )
        supplier = supplier_result.scalars().first()
        if not supplier or product.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this product")

        for field, value in product_data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def delete_product(product_id: int, db: AsyncSession) -> dict[str, str]:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        await db.delete(product)
        await db.commit()
        return {"message": "Product deleted successfully"}
