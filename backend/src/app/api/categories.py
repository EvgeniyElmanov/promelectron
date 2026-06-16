from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.category import CategoryCreate, CategoryListOut, CategoryOut
from src.app.services.category_service import CategoryService
from src.app.utils.auth import get_current_active_admin
from src.app.utils.cache import cache_response, invalidate_cache

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryOut)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    category = await CategoryService.create_category(category_data=category_data, db=db)
    await invalidate_cache("/api/v1/categories*")
    return category


@router.get("/{category_id}", response_model=CategoryOut)
async def read_category(category_id: int, db: AsyncSession = Depends(get_db)):
    return await CategoryService.get_category(category_id=category_id, db=db)


@router.get("/", response_model=CategoryListOut)
@cache_response(ttl_seconds=3600)
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    parent_id: int | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await CategoryService.list_categories(
        db=db, skip=skip, limit=limit, parent_id=parent_id, q=q
    )
    return CategoryListOut(items=items, total=total)


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    category = await CategoryService.update_category(
        category_id=category_id, category_data=category_data, db=db
    )
    await invalidate_cache("/api/v1/categories*")
    return category


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await CategoryService.delete_category(category_id=category_id, db=db)
    await invalidate_cache("/api/v1/categories*")
    return result
