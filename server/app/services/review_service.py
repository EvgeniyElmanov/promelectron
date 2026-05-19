from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.models.product import Product
from server.app.models.review import Review
from server.app.models.user import User
from server.app.schemas.review import ReviewCreate, ReviewUpdate


class ReviewService:
    @staticmethod
    async def create_review(
        product_id: int, review_data: ReviewCreate, current_user: User, db: AsyncSession
    ) -> Review:
        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        existing = await db.execute(
            select(Review).where(
                Review.product_id == product_id, Review.user_id == current_user.id
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="You already reviewed this product")

        review = Review(
            user_id=current_user.id,
            product_id=product_id,
            rating=review_data.rating,
            text=review_data.text,
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        return review

    @staticmethod
    async def get_reviews(product_id: int, db: AsyncSession) -> list[Review]:
        result = await db.execute(
            select(Review)
            .where(Review.product_id == product_id, Review.is_approved.is_(True))
            .order_by(Review.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_review(review_id: int, db: AsyncSession) -> Review:
        result = await db.execute(select(Review).where(Review.id == review_id))
        review = result.scalars().first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review

    @staticmethod
    async def update_review(
        review_id: int, review_data: ReviewUpdate, current_user: User, db: AsyncSession
    ) -> Review:
        review = await ReviewService.get_review(review_id, db)
        if review.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this review")

        for field, value in review_data.model_dump(exclude_unset=True).items():
            setattr(review, field, value)

        await db.commit()
        await db.refresh(review)
        return review

    @staticmethod
    async def delete_review(review_id: int, current_user: User, db: AsyncSession) -> dict[str, str]:
        review = await ReviewService.get_review(review_id, db)
        if review.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this review")

        await db.delete(review)
        await db.commit()
        return {"message": "Review deleted successfully"}

    @staticmethod
    async def get_average_rating(product_id: int, db: AsyncSession) -> float:
        result = await db.execute(
            select(func.avg(Review.rating)).where(
                Review.product_id == product_id, Review.is_approved.is_(True)
            )
        )
        avg = result.scalar()
        return round(avg, 1) if avg else 0.0
