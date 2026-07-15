import hmac
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.api.seed import SEED_SECRET
from src.app.core.config import settings
from src.app.db.database import get_db
from src.app.models.order import Order
from src.app.models.payment import Payment
from src.app.models.user import User
from src.app.schemas.payment import PaymentCreateResponse, PaymentDebugSetStatusRequest, PaymentOut
from src.app.services.payment_service import PaymentService
from src.app.services.yookassa_service import YooKassaService
from src.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/payments", tags=["payments"])


class GuestPaymentRequest(BaseModel):
    guest_email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class GuestMockConfirmRequest(BaseModel):
    guest_email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


@router.post("/{order_id}/", response_model=PaymentCreateResponse)
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


@router.post("/guest/{order_id}/", response_model=PaymentCreateResponse)
async def create_guest_payment(
    order_id: int,
    request_data: GuestPaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Создать платёж для гостевого заказа через ЮKassa."""
    payment = await PaymentService.create_guest_payment(
        order_id=order_id, guest_email=request_data.guest_email, db=db
    )
    return PaymentCreateResponse(
        payment_id=payment.id,
        status=payment.status,
        confirmation_url=payment.confirmation_url,
        amount=payment.amount,
    )


@router.post("/guest/{order_id}/mock-confirm/", response_model=PaymentOut)
async def mock_confirm_guest_payment(
    order_id: int,
    request_data: GuestMockConfirmRequest | None = Body(None),
    guest_email: str | None = Query(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    db: AsyncSession = Depends(get_db),
):
    """Подтвердить mock-платёж для гостевого заказа (для dev-режима).

    Email можно передать либо в теле, либо query-параметром `guest_email`.
    """
    email = (request_data.guest_email if request_data else None) or guest_email
    if not email:
        raise HTTPException(status_code=422, detail="guest_email is required")
    payment = await PaymentService.confirm_guest_mock_payment_by_order(
        order_id=order_id, guest_email=email, db=db
    )
    return payment


@router.post("/{order_id}/mock-confirm/", response_model=PaymentOut)
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


@router.get("/{payment_id}/", response_model=PaymentOut)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить информацию о платеже."""
    payment = await PaymentService.get_payment(payment_id=payment_id, user_id=current_user.id, db=db)
    return payment


@router.post("/{payment_id}/cancel/", response_model=PaymentOut)
async def cancel_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Отменить платёж (если ещё не оплачен)."""
    payment = await PaymentService.cancel_payment(payment_id=payment_id, user_id=current_user.id, db=db)
    return payment


@router.post("/{payment_id}/sync/", response_model=PaymentOut)
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


@router.post("/sync-by-order/{order_id}/", response_model=PaymentOut)
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


@router.post("/debug/yookassa/create/")
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


@router.post("/debug/set-status/", response_model=PaymentOut)
async def debug_set_payment_status(
    request_data: PaymentDebugSetStatusRequest,
    x_seed_secret: str | None = Header(None, alias="x-seed-secret"),
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint: детерминированно перевести платёж в `succeeded` или `canceled`.

    Доступен только при `YOOKASSA_TEST_MODE=true` и с заголовком `x-seed-secret`.
    Используется в E2E-тестах для обхода нестабильного UI sandbox ЮKassa.
    """
    if not settings.yookassa_test_mode:
        raise HTTPException(status_code=403, detail="Debug endpoint only available in test mode")

    if x_seed_secret is None or not hmac.compare_digest(x_seed_secret, SEED_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")

    query = (
        select(Payment)
        .where(Payment.order_id == request_data.order_id)
        .options(
            selectinload(Payment.order).selectinload(Order.items),
            selectinload(Payment.order).selectinload(Order.recipient),
            selectinload(Payment.order).selectinload(Order.cdek_order),
        )
    )

    result = await db.execute(query)
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    order = payment.order
    if order is None:
        raise HTTPException(status_code=500, detail="Order not loaded for payment")

    if request_data.guest_email is not None:
        if order.user_id is not None:
            raise HTTPException(status_code=400, detail="Order is not a guest order")
        email_match = await db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.id == order.id,
                Order.user_id.is_(None),
                func.lower(Order.guest_email) == request_data.guest_email.lower(),
            )
        )
        if not email_match:
            raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id is None and request_data.guest_email is None:
        raise HTTPException(status_code=400, detail="guest_email is required for guest orders")

    if payment.status in ("paid", "cancelled"):
        raise HTTPException(status_code=400, detail="Payment is in terminal status")

    payment.updated_at = datetime.now(timezone.utc)

    if request_data.status == "succeeded":
        payment.yookassa_status = "succeeded"
        await PaymentService._process_successful_payment(payment, db)
    else:
        payment.status = "cancelled"
        payment.yookassa_status = "canceled"
        PaymentService._store_cancellation_details(
            payment, {"reason": request_data.cancellation_reason, "party": "yoo_money"}
        )
        await db.commit()

    await db.refresh(payment)
    return payment


@router.post("/yookassa/webhook/")
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
