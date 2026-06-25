from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.order import Order
from src.app.models.recipient import Recipient


class RecipientService:
    @staticmethod
    async def list_for_user(user_id: int, db: AsyncSession) -> list[Recipient]:
        result = await db.execute(
            select(Recipient)
            .where(Recipient.user_id == user_id)
            .order_by(Recipient.is_default.desc(), Recipient.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_for_user(user_id: int, recipient_id: int, db: AsyncSession) -> Recipient:
        result = await db.execute(
            select(Recipient).where(Recipient.id == recipient_id, Recipient.user_id == user_id)
        )
        recipient = result.scalars().first()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        return recipient

    @staticmethod
    async def create(
        user_id: int,
        first_name: str,
        last_name: str,
        phone: str,
        patronymic: str | None,
        country_code: str,
        is_default: bool,
        db: AsyncSession,
        commit: bool = True,
    ) -> Recipient:
        if is_default:
            await RecipientService._reset_default(user_id, db)

        recipient = Recipient(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            patronymic=patronymic,
            phone=phone,
            country_code=country_code,
            is_default=is_default,
        )
        db.add(recipient)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(recipient)
        return recipient

    @staticmethod
    async def update(
        user_id: int,
        recipient_id: int,
        first_name: str | None,
        last_name: str | None,
        phone: str | None,
        patronymic: str | None,
        country_code: str | None,
        is_default: bool | None,
        db: AsyncSession,
    ) -> Recipient:
        recipient = await RecipientService.get_for_user(user_id, recipient_id, db)

        if is_default is True:
            await RecipientService._reset_default(user_id, db)

        if first_name is not None:
            recipient.first_name = first_name
        if last_name is not None:
            recipient.last_name = last_name
        if phone is not None:
            recipient.phone = phone
        if patronymic is not None:
            recipient.patronymic = patronymic
        if country_code is not None:
            recipient.country_code = country_code
        if is_default is not None:
            recipient.is_default = is_default

        await db.commit()
        await db.refresh(recipient)
        return recipient

    @staticmethod
    async def delete(user_id: int, recipient_id: int, db: AsyncSession) -> None:
        recipient = await RecipientService.get_for_user(user_id, recipient_id, db)

        order_count_result = await db.execute(
            select(func.count(Order.id)).where(Order.recipient_id == recipient_id)
        )
        if order_count_result.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete recipient linked to existing orders",
            )

        await db.delete(recipient)
        await db.commit()

    @staticmethod
    async def set_default(user_id: int, recipient_id: int, db: AsyncSession) -> Recipient:
        recipient = await RecipientService.get_for_user(user_id, recipient_id, db)
        await RecipientService._reset_default(user_id, db)
        recipient.is_default = True
        await db.commit()
        await db.refresh(recipient)
        return recipient

    @staticmethod
    async def _reset_default(user_id: int, db: AsyncSession) -> None:
        result = await db.execute(
            select(Recipient).where(Recipient.user_id == user_id, Recipient.is_default.is_(True))
        )
        for r in result.scalars().all():
            r.is_default = False
