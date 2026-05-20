from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.category import CategoryCreate, CategoryOut
from src.app.services.category_service import CategoryService
from src.app.utils.auth import get_current_active_admin

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryOut)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    return await CategoryService.create_category(category_data=category_data, db=db)


@router.get("/{category_id}", response_model=CategoryOut)
async def read_category(category_id: int, db: AsyncSession = Depends(get_db)):
    return await CategoryService.get_category(category_id=category_id, db=db)


@router.get("/", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService.list_categories(db=db)


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    return await CategoryService.update_category(
        category_id=category_id, category_data=category_data, db=db
    )


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    return await CategoryService.delete_category(category_id=category_id, db=db)

