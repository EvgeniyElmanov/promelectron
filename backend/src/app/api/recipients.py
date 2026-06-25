from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.recipient import RecipientCreate, RecipientOut, RecipientUpdate
from src.app.services.recipient_service import RecipientService
from src.app.utils.auth import get_current_user
from src.app.utils.rate_limiter import conditional_limit

router = APIRouter(prefix="/me/recipients", tags=["recipients"])


@router.get("/", response_model=list[RecipientOut])
@conditional_limit("100/minute")
async def list_recipients(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Список сохранённых получателей текущего пользователя."""
    return await RecipientService.list_for_user(user_id=current_user.id, db=db)


@router.post("/", response_model=RecipientOut)
@conditional_limit("100/minute")
async def create_recipient(
    request: Request,
    data: RecipientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать нового получателя."""
    return await RecipientService.create(
        user_id=current_user.id,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        patronymic=data.patronymic,
        country_code=data.country_code,
        is_default=data.is_default,
        db=db,
    )


@router.patch("/{recipient_id}/", response_model=RecipientOut)
@conditional_limit("100/minute")
async def update_recipient(
    request: Request,
    recipient_id: int,
    data: RecipientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить получателя."""
    return await RecipientService.update(
        user_id=current_user.id,
        recipient_id=recipient_id,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        patronymic=data.patronymic,
        country_code=data.country_code,
        is_default=data.is_default,
        db=db,
    )


@router.delete("/{recipient_id}/")
@conditional_limit("100/minute")
async def delete_recipient(
    request: Request,
    recipient_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить получателя."""
    await RecipientService.delete(user_id=current_user.id, recipient_id=recipient_id, db=db)
    return {"message": "Recipient deleted"}


@router.post("/{recipient_id}/set-default/", response_model=RecipientOut)
@conditional_limit("100/minute")
async def set_default_recipient(
    request: Request,
    recipient_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Сделать получателя по умолчанию."""
    return await RecipientService.set_default(
        user_id=current_user.id,
        recipient_id=recipient_id,
        db=db,
    )
