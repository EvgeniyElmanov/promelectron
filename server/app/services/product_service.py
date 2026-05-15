from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.models.category import Category
from server.app.models.favorite import Favorite
from server.app.models.product import Product
from server.app.models.review import Review
from server.app.models.supplier import Supplier
from server.app.models.user import User
from server.app.schemas.product import ProductCreate, ProductUpdate
from server.app.services.favorite_service import FavoriteService
from server.app.services.review_service import ReviewService


class ProductService:
    @staticmethod
    async def read_products(
        skip: int,
        limit: int,
        db: AsyncSession,
        search: str | None = None,
        category_id: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort_by: str | None = None,
    ) -> list[Product]:
        query = select(Product).where(Product.is_active == True)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                )
            )

        if category_id is not None:
            query = query.where(Product.category_id == category_id)

        if min_price is not None:
            query = query.where(Product.price >= min_price)

        if max_price is not None:
            query = query.where(Product.price <= max_price)

        match sort_by:
            case "price_asc":
                query = query.order_by(Product.price.asc())
            case "price_desc":
                query = query.order_by(Product.price.desc())
            case "newest":
                query = query.order_by(Product.created_at.desc())
            case _:
                query = query.order_by(Product.id.desc())

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def read_products_by_supplier(
        supplier_id: int,
        skip: int,
        limit: int,
        db: AsyncSession,
    ) -> list[Product]:
        query = (
            select(Product)
            .where(Product.supplier_id == supplier_id)
            .order_by(Product.id.desc())
        )
        result = await db.execute(query.offset(skip).limit(limit))
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
    async def read_product_detail(
        product_id: int, current_user: User | None, db: AsyncSession
    ) -> dict:
        product = await ProductService.read_product(product_id, db)

        reviews = await ReviewService.get_reviews(product_id, db)
        avg_rating = await ReviewService.get_average_rating(product_id, db)

        is_favorite = False
        if current_user:
            is_favorite = await FavoriteService.is_favorite(product_id, current_user, db)

        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "is_active": product.is_active,
            "category_id": product.category_id,
            "supplier_id": product.supplier_id,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "reviews": reviews,
            "average_rating": avg_rating,
            "reviews_count": len(reviews),
            "is_favorite": is_favorite,
        }

    @staticmethod
    async def delete_product(
        product_id: int, current_user: User, db: AsyncSession
    ) -> dict[str, str]:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        supplier_result = await db.execute(
            select(Supplier).where(Supplier.user_id == current_user.id)
        )
        supplier = supplier_result.scalars().first()
        if not supplier or product.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this product")

        product.is_active = False
        await db.commit()
        return {"message": "Product deactivated successfully"}
