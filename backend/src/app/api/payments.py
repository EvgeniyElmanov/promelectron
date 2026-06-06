from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.payment import PaymentCreateResponse, PaymentOut
from src.app.services.payment_service import PaymentService
from src.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{order_id}", response_model=PaymentCreateResponse)
async def create_payment(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать платёж для заказа через ЮKassa."""
    payment = await PaymentService.create_payment(order_id=order_id, user_id=current_user.id, db=db)
    return PaymentCreateResponse(
        payment_id=payment.id,
        status=payment.status,
        confirmation_url=payment.confirmation_url,
        amount=payment.amount,
    )


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


@router.post("/{payment_id}/sync", response_model=PaymentOut)
async def sync_payment_status(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Синхронизировать статус платежа с ЮKassa (ручная проверка).

    Полезно когда webhook не пришёл или нужно принудительно обновить статус.
    """
    payment = await PaymentService.sync_payment_status(payment_id=payment_id, user_id=current_user.id, db=db)
    return payment


@router.post("/sync-by-order/{order_id}", response_model=PaymentOut)
async def sync_payment_status_by_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Синхронизировать статус платежа по ID заказа.

    Frontend-friendly endpoint — не нужно знать payment_id.
    """
    payment = await PaymentService.sync_payment_status_by_order(order_id=order_id, user_id=current_user.id, db=db)
    return payment


@router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Входящий webhook от ЮKassa."""
    payload = await request.json()
    signature = request.headers.get("X-YooKassa-Signature")
    await PaymentService.handle_webhook(payload=payload, signature=signature, db=db)
    return {"status": "ok"}
