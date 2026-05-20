from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.notification import Notification
from src.app.schemas.notification import NotificationOut


class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: int,
        type: str,
        title: str,
        message: str,
        order_id: int | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            order_id=order_id,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Send real-time notification via WebSocket
        try:
            from src.app.api.ws import notify_user
            await notify_user(
                user_id,
                {
                    "type": "notification",
                    "data": NotificationOut.model_validate(notification).model_dump(mode="json"),
                },
            )
        except Exception:
            pass  # WebSocket не критичен

        return notification

    @staticmethod
    async def get_notifications(
        user_id: int, db: AsyncSession, skip: int = 0, limit: int = 50, unread_only: bool = False
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def mark_as_read(notification_id: int, user_id: int, db: AsyncSession) -> Notification | None:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        notification = result.scalars().first()
        if not notification:
            return None
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return notification

    @staticmethod
    async def mark_all_as_read(user_id: int, db: AsyncSession) -> int:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        notifications = result.scalars().all()
        count = 0
        for n in notifications:
            n.is_read = True
            count += 1
        if count:
            await db.commit()
        return count

    @staticmethod
    async def get_unread_count(user_id: int, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return result.scalar() or 0

    @staticmethod
    async def delete_notification(notification_id: int, user_id: int, db: AsyncSession) -> bool:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        notification = result.scalars().first()
        if not notification:
            return False
        await db.delete(notification)
        await db.commit()
        return True
