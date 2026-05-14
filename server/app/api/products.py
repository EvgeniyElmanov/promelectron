from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.product import ProductCreate, ProductDetailOut, ProductOut, ProductUpdate
from server.app.services.product_service import ProductService
from server.app.utils.auth import (
    get_current_active_admin,
    get_current_active_supplier,
    get_optional_user,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductOut])
async def read_products(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await ProductService.read_products(skip=skip, limit=limit, db=db)


@router.post("/", response_model=ProductOut)
async def create_product(
    product_: ProductCreate,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    return await ProductService.create_product(
        product_data=product_, current_user=current_user, db=db
    )


@router.get("/{product_id}", response_model=ProductOut)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    return await ProductService.read_product(product_id=product_id, db=db)


@router.get("/{product_id}/detail", response_model=ProductDetailOut)
async def read_product_detail(
    product_id: int,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProductService.read_product_detail(
        product_id=product_id, current_user=current_user, db=db
    )


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    product_: ProductUpdate,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    return await ProductService.update_product(
        product_id=product_id, product_data=product_, current_user=current_user, db=db
    )


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    return await ProductService.delete_product(product_id=product_id, db=db)

