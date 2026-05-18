from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.notification import NotificationList, NotificationOut
from server.app.services.notification_service import NotificationService
from server.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationList)
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список уведомлений текущего пользователя."""
    items = await NotificationService.get_notifications(
        user_id=current_user.id, db=db, skip=skip, limit=limit, unread_only=unread_only
    )
    unread_count = await NotificationService.get_unread_count(user_id=current_user.id, db=db)
    return NotificationList(
        items=[NotificationOut.model_validate(n) for n in items],
        unread_count=unread_count,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить количество непрочитанных уведомлений."""
    count = await NotificationService.get_unread_count(user_id=current_user.id, db=db)
    return {"count": count}


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Отметить уведомление как прочитанное."""
    notification = await NotificationService.mark_as_read(
        notification_id=notification_id, user_id=current_user.id, db=db
    )
    if not notification:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationOut.model_validate(notification)


@router.patch("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Отметить все уведомления как прочитанные."""
    count = await NotificationService.mark_all_as_read(user_id=current_user.id, db=db)
    return {"marked_as_read": count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить уведомление."""
    success = await NotificationService.delete_notification(
        notification_id=notification_id, user_id=current_user.id, db=db
    )
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"detail": "Notification deleted"}
