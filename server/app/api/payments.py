from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.payment import PaymentCreateResponse, PaymentOut
from server.app.services.payment_service import PaymentService
from server.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{order_id}", response_model=PaymentCreateResponse)
async def create_payment(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать платёж для заказа."""
    payment = await PaymentService.create_payment(order_id=order_id, user_id=current_user.id, db=db)
    return PaymentCreateResponse(
        payment_id=payment.id,
        status=payment.status,
        confirmation_url=f"/checkout/{order_id}/pay",
        amount=payment.amount,
    )


@router.post("/{payment_id}/confirm", response_model=PaymentOut)
async def confirm_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Подтвердить платёж (mock callback от платёжного шлюза)."""
    # Проверяем доступ
    await PaymentService.get_payment(payment_id=payment_id, user_id=current_user.id, db=db)
    payment = await PaymentService.confirm_payment(payment_id=payment_id, db=db)
    return payment


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить информацию о платеже."""
    payment = await PaymentService.get_payment(payment_id=payment_id, user_id=current_user.id, db=db)
    return payment


@router.post("/{payment_id}/cancel", response_model=PaymentOut)
async def cancel_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Отменить платёж (если ещё не оплачен)."""
    payment = await PaymentService.cancel_payment(payment_id=payment_id, user_id=current_user.id, db=db)
    return payment
