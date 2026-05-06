from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.category import CategoryCreate, CategoryOut
from server.app.services.category_service import CategoryService
from server.app.utils.auth import get_current_active_admin

router = APIRouter()


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

