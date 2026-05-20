from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.favorite import FavoriteOut, FavoriteWithProduct
from src.app.services.favorite_service import FavoriteService
from src.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/add/{product_id}", response_model=FavoriteOut)
async def add_to_favorites(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await FavoriteService.add_to_favorites(
        product_id=product_id, current_user=current_user, db=db
    )


@router.delete("/remove/{product_id}")
async def remove_from_favorites(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await FavoriteService.remove_from_favorites(
        product_id=product_id, current_user=current_user, db=db
    )


@router.get("/", response_model=List[FavoriteWithProduct])
async def get_favorites(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await FavoriteService.get_favorites(current_user=current_user, db=db)
