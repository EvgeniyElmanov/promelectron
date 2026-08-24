from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.attribute import Attribute, ProductAttributeValue
from src.app.models.category import Category
from src.app.models.product import Product, site_price_expression
from src.app.models.review import Review
from src.app.models.supplier import Supplier
from src.app.models.user import User
from src.app.schemas.product import ProductCreate, ProductUpdate
from src.app.services.favorite_service import FavoriteService
from src.app.services.price_service import upsert_product_price
from src.app.services.review_service import ReviewService


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
        min_rating: float | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[Product], int]:
        filters = [Product.is_active.is_(True)]

        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                )
            )

        if category_id is not None:
            filters.append(Product.category_id == category_id)

        if min_price is not None:
            # Подзапрос сайтовой цены: товары без строки product_prices
            # (NULL) в ценовой фильтр не попадают
            filters.append(site_price_expression() >= min_price)

        if max_price is not None:
            filters.append(site_price_expression() <= max_price)

        # Build count query with same filters
        count_query = select(func.count(Product.id)).where(and_(*filters))

        if min_rating is not None:
            avg_subq = (
                select(func.avg(Review.rating))
                .where(Review.product_id == Product.id)
                .scalar_subquery()
            )
            count_query = count_query.where(avg_subq >= min_rating)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Build select query
        query = select(Product).where(and_(*filters))

        if min_rating is not None:
            avg_subq = (
                select(func.avg(Review.rating))
                .where(Review.product_id == Product.id)
                .scalar_subquery()
            )
            query = query.where(avg_subq >= min_rating)

        match sort_by:
            case "price_asc":
                query = query.order_by(site_price_expression().asc().nulls_last())
            case "price_desc":
                query = query.order_by(site_price_expression().desc().nulls_last())
            case "newest":
                query = query.order_by(Product.created_at.desc())
            case "name_asc":
                query = query.order_by(Product.name.asc())
            case "rating_desc":
                avg_sort_subq = (
                    select(func.coalesce(func.avg(Review.rating), 0))
                    .where(Review.product_id == Product.id)
                    .scalar_subquery()
                )
                query = query.order_by(avg_sort_subq.desc())
            case _:
                query = query.order_by(Product.id.desc())

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

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

        data = product_data.model_dump()
        # price — column_property (read-only): в конструктор не передаём,
        # пишем сайтовой строкой product_prices после flush (D-13)
        price = data.pop("price")
        if data.get("images") is None:
            data["images"] = []
        new_product = Product(**data, supplier_id=supplier.id)
        db.add(new_product)
        await db.flush()
        await upsert_product_price(db, new_product.id, settings.onec_site_price_type, price)
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

        update_data = product_data.model_dump(exclude_unset=True)
        # price — column_property (read-only): из setattr-цикла исключаем,
        # обновляем сайтовую строку product_prices (D-13)
        price = update_data.pop("price", None)
        for field, value in update_data.items():
            setattr(product, field, value)
        if price is not None:
            await upsert_product_price(db, product.id, settings.onec_site_price_type, price)

        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def read_product_detail(
        product_id: int, current_user: User | None, db: AsyncSession
    ) -> dict:
        product = await ProductService.read_product(product_id, db)

        # Атрибуты товара одним запросом (без N+1, паттерн search_indexing._load_attribute_values)
        attr_result = await db.execute(
            select(
                ProductAttributeValue.value_number,
                ProductAttributeValue.value_text,
                ProductAttributeValue.value_bool,
                Attribute.code,
                Attribute.name,
                Attribute.value_type,
                Attribute.unit,
            )
            .join(Attribute, ProductAttributeValue.attribute_id == Attribute.id)
            .where(ProductAttributeValue.product_id == product_id)
            .order_by(Attribute.sort, Attribute.name)
        )
        attributes: list[dict] = []
        for value_number, value_text, value_bool, code, name, value_type, unit in attr_result.all():
            if value_number is not None:
                value: float | bool | str = float(value_number)
            elif value_bool is not None:
                value = bool(value_bool)
            elif value_text is not None:
                value = value_text
            else:
                continue
            attributes.append(
                {
                    "code": code,
                    "name": name,
                    "value_type": value_type,
                    "value": value,
                    "unit": unit,
                }
            )

        reviews = await ReviewService.get_reviews(product_id, db)
        avg_rating = await ReviewService.get_average_rating(product_id, db)

        is_favorite = False
        if current_user:
            is_favorite = await FavoriteService.is_favorite(product_id, current_user, db)

        return {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "weight_grams": product.weight_grams,
            "length_cm": product.length_cm,
            "width_cm": product.width_cm,
            "height_cm": product.height_cm,
            "is_active": product.is_active,
            "category_id": product.category_id,
            "supplier_id": product.supplier_id,
            "images": product.images or [],
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "attributes": attributes,
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
