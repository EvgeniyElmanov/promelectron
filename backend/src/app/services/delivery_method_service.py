from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.delivery_method import DeliveryMethod
from src.app.schemas.delivery_method import DeliveryMethodCreate, DeliveryMethodUpdate


class DeliveryMethodService:
    @staticmethod
    async def get_methods(db: AsyncSession) -> list[DeliveryMethod]:
        result = await db.execute(select(DeliveryMethod).where(DeliveryMethod.is_active.is_(True)))
        return list(result.scalars().all())

    @staticmethod
    async def get_method(method_id: int, db: AsyncSession) -> DeliveryMethod:
        result = await db.execute(select(DeliveryMethod).where(DeliveryMethod.id == method_id))
        method = result.scalars().first()
        if not method:
            raise HTTPException(status_code=404, detail="Delivery method not found")
        return method

    @staticmethod
    async def create_method(data: DeliveryMethodCreate, db: AsyncSession) -> DeliveryMethod:
        method = DeliveryMethod(**data.model_dump())
        db.add(method)
        await db.commit()
        await db.refresh(method)
        return method

    @staticmethod
    async def update_method(method_id: int, data: DeliveryMethodUpdate, db: AsyncSession) -> DeliveryMethod:
        method = await DeliveryMethodService.get_method(method_id, db)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(method, field, value)
        await db.commit()
        await db.refresh(method)
        return method

    @staticmethod
    async def delete_method(method_id: int, db: AsyncSession) -> dict[str, str]:
        method = await DeliveryMethodService.get_method(method_id, db)
        method.is_active = False
        await db.commit()
        return {"message": "Delivery method deactivated"}
