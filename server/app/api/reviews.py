from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate
from server.app.services.review_service import ReviewService
from server.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/product/{product_id}", response_model=ReviewOut)
async def create_review(
    product_id: int,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReviewService.create_review(
        product_id=product_id, review_data=review_data, current_user=current_user, db=db
    )


@router.get("/product/{product_id}", response_model=List[ReviewOut])
async def get_product_reviews(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await ReviewService.get_reviews(product_id=product_id, db=db)


@router.put("/{review_id}", response_model=ReviewOut)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReviewService.update_review(
        review_id=review_id, review_data=review_data, current_user=current_user, db=db
    )


@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReviewService.delete_review(
        review_id=review_id, current_user=current_user, db=db
    )
