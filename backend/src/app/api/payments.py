from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.payment import PaymentCreateResponse, PaymentOut
from src.app.services.payment_service import PaymentService
from src.app.services.yookassa_service import YooKassaService
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


@router.post("/{order_id}/mock-confirm", response_model=PaymentOut)
async def mock_confirm_payment(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Подтвердить mock-платёж (для dev-режима без реальной YooKassa)."""
    payment = await PaymentService.confirm_mock_payment_by_order(
        order_id=order_id, user_id=current_user.id, db=db
    )
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


@router.post("/debug/yookassa/create")
async def debug_yookassa_create(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Debug endpoint: создать тестовый платёж напрямую в YooKassa без DB.

    Доступен только при YOOKASSA_TEST_MODE=true.
    Полезен для диагностики: сравниваем прямой curl vs backend SDK.
    """
    if not settings.yookassa_test_mode:
        raise HTTPException(status_code=403, detail="Debug endpoint only available in test mode")

    body = await request.json()
    amount = Decimal(str(body.get("amount", "10.00")))
    order_id = body.get("order_id", 0)

    result = await YooKassaService.create_payment(
        order_id=order_id,
        amount=amount,
        description=f"Debug payment order={order_id}",
        user_id=current_user.id,
    )
    return result


@router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Входящий webhook от ЮKassa.

    Считываем raw_body ДО json(), чтобы корректно проверять подпись webhook.
    """
    raw_body = await request.body()
    payload = await request.json()
    signature = request.headers.get("X-YooKassa-Signature")
    await PaymentService.handle_webhook(
        payload=payload,
        raw_body=raw_body.decode("utf-8"),
        signature=signature,
        db=db,
    )
    return {"status": "ok"}
