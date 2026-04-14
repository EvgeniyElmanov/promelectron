from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.category import Category
from schemas.category import CategoryCreate, CategoryUpdate, CategoryOut
from utils.auth import get_current_active_admin
from models.user import User

router = APIRouter()

@router.post("/", response_model=CategoryOut)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
):
    # Проверим, существует ли родительская категория
    if category_data.parent_id:
        parent_result = await db.execute(
            select(Category).where(Category.id == category_data.parent_id)
        )
        parent = parent_result.scalars().first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")

    new_category = Category(**category_data.model_dump())
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category

@router.get("/{category_id}", response_model=CategoryOut)
async def read_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.get("/", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    return categories