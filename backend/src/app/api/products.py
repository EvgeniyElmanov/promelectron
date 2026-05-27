import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.supplier import Supplier
from src.app.models.user import User
from src.app.schemas.product import ProductCreate, ProductDetailOut, ProductListOut, ProductOut, ProductUpdate
from src.app.services.product_service import ProductService
from src.app.services.storage_service import storage
from src.app.utils.auth import (
    get_current_active_supplier,
    get_optional_user,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=ProductListOut)
async def read_products(
    skip: int = 0,
    limit: int = 20,
    q: str | None = None,
    category_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    sort_by: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await ProductService.read_products(
        skip=skip,
        limit=limit,
        db=db,
        search=q,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        sort_by=sort_by,
    )
    return {"items": items, "total": total}


@router.post("/", response_model=ProductOut)
async def create_product(
    product_: ProductCreate,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    return await ProductService.create_product(
        product_data=product_, current_user=current_user, db=db
    )


@router.get("/my", response_model=List[ProductOut])
async def read_my_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.user_id == current_user.id)
    )
    supplier = supplier_result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=403, detail="You are not registered as a supplier")
    return await ProductService.read_products_by_supplier(
        supplier_id=supplier.id, skip=skip, limit=limit, db=db
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
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    return await ProductService.delete_product(
        product_id=product_id, current_user=current_user, db=db
    )


# --- Product Images ---

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _validate_image(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    return ext


@router.post("/{product_id}/images", response_model=ProductOut)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    ext = _validate_image(file)

    # Verify product exists and belongs to supplier
    product = await ProductService.read_product(product_id=product_id, db=db)
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.user_id == current_user.id)
    )
    supplier = supplier_result.scalars().first()
    if not supplier or product.supplier_id != supplier.id:
        raise HTTPException(status_code=403, detail="Not your product")

    # Upload to storage
    key = f"products/{product_id}/{uuid.uuid4().hex}{ext}"
    image_url = await storage.upload(key, file)

    # Update product.images
    images = product.images or []
    images.append(image_url)
    return await ProductService.update_product(
        product_id=product_id,
        product_data=ProductUpdate(images=images),
        current_user=current_user,
        db=db,
    )


@router.delete("/{product_id}/images/{filename}", response_model=ProductOut)
async def delete_product_image(
    product_id: int,
    filename: str,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    # Verify product exists and belongs to supplier
    product = await ProductService.read_product(product_id=product_id, db=db)
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.user_id == current_user.id)
    )
    supplier = supplier_result.scalars().first()
    if not supplier or product.supplier_id != supplier.id:
        raise HTTPException(status_code=403, detail="Not your product")

    # Validate filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Find matching image URL in product.images
    image_url = None
    for img in (product.images or []):
        if img.endswith(f"/{safe_filename}"):
            image_url = img
            break

    if image_url is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete from storage
    await storage.delete(image_url)

    # Update product.images
    images = [img for img in (product.images or []) if img != image_url]
    return await ProductService.update_product(
        product_id=product_id,
        product_data=ProductUpdate(images=images),
        current_user=current_user,
        db=db,
    )
