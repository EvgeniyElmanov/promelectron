from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.product import Product
from models.category import Category
from schemas.product import ProductCreate, ProductUpdate, ProductOut
from schemas.category import CategoryOut
from utils.auth import get_current_active_supplier, get_current_active_admin
from models.user import User

router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", response_model=ProductOut)
async def create_product(
    product_: ProductCreate,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db)
):
    # Проверим, существует ли категория
    if product_.category_id:
        category_result = await db.execute(
            select(Category).where(Category.id == product_.category_id)
        )
        category = category_result.scalars().first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    # Создаём товар
    new_product = Product(**product_.model_dump())
    # new_product.supplier_id = current_user.id  # ← Закомментировано

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    return new_product

@router.get("/{product_id}", response_model=ProductOut)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    product_: ProductUpdate,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.supplier_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this product")

    for field, value in product_.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return {"message": "Product deleted successfully"}