import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.core.config import settings
from src.app.models.cart import Cart, CartItem
from src.app.models.order import Order, OrderItem
from src.app.models.payment import Payment
from src.app.models.user import User
from src.app.services.email_service import EmailService
from src.app.services.notification_service import NotificationService
from src.app.services.yookassa_service import YooKassaService

logger = logging.getLogger(__name__)


class PaymentService:
    @staticmethod
    async def create_payment(order_id: int, user_id: int, db: AsyncSession) -> Payment:
        """Создать платёж для заказа через ЮKassa."""
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.user),
            )
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "pending":
            raise HTTPException(status_code=400, detail="Order is not in pending status")

        # Проверяем, не создан ли платёж ранее
        existing_result = await db.execute(select(Payment).where(Payment.order_id == order_id))
        existing_payment = existing_result.scalars().first()
        if existing_payment:
            if existing_payment.status == "paid":
                raise HTTPException(status_code=400, detail="Order is already paid")
            # Возвращаем существующий платёж, чтобы frontend мог перейти к оплате
            return existing_payment

        # Build receipt data for 54-FZ (only for non-self-employed merchants)
        receipt_data = None
        if settings.yookassa_receipt_enabled:
            customer_email = None
            if order.user and order.user.email:
                customer_email = order.user.email
            elif order.guest_email:
                customer_email = order.guest_email

            if customer_email and order.items:
                receipt_items = []
                for oi in order.items:
                    receipt_items.append(
                        {
                            "description": (oi.product.name if oi.product else "Товар")[:128],
                            "quantity": f"{oi.quantity:.2f}",
                            "amount": {
                                "value": f"{float(oi.price_at_time * oi.quantity):.2f}",
                                "currency": "RUB",
                            },
                            "vat_code": settings.yookassa_vat_code,
                            "payment_subject": "commodity",
                            "payment_mode": "full_payment",
                        }
                    )
                receipt_data = {
                    "customer": {"email": customer_email},
                    "items": receipt_items,
                    "tax_system_code": settings.yookassa_tax_system_code,
                }

        # Создаём платёж в ЮKassa (или mock для dev-режима)
        if YooKassaService.is_configured():
            yookassa_result = await YooKassaService.create_payment(
                order_id=order.id,
                amount=order.total_price,
                description=f"Заказ №{order.id}",
                user_id=order.user_id,
                receipt_data=receipt_data,
            )
        else:
            logger.info("YooKassa not configured — creating mock payment for order %s", order.id)
            yookassa_result = {
                "yookassa_payment_id": f"mock-{uuid.uuid4()}",
                "status": "pending",
                "confirmation_url": f"{settings.frontend_url.rstrip('/')}/payment/success?order_id={order.id}&mock=1",
                "amount": order.total_price,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "test": True,
            }

        payment = Payment(
            order_id=order.id,
            amount=order.total_price,
            status="pending",
            provider_payment_id=yookassa_result["yookassa_payment_id"],
            yookassa_payment_id=yookassa_result["yookassa_payment_id"],
            yookassa_status=yookassa_result["status"],
            confirmation_url=yookassa_result["confirmation_url"],
            yookassa_created_at=datetime.fromisoformat(
                yookassa_result["created_at"].replace("Z", "+00:00")
            ),
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return payment

    @staticmethod
    async def _process_successful_payment(payment: Payment, db: AsyncSession) -> None:
        """Обработка успешной оплаты: обновление статусов, очистка корзины, уведомления."""
        if payment.status == "paid":
            logger.info("Payment %s already marked as paid, skipping side-effects", payment.id)
            return

        if payment.order is None:
            logger.warning("Payment %s has no associated order, skipping side-effects", payment.id)
            return

        # Загружаем данные ДО commit, чтобы избежать lazy-load после expire в async SQLAlchemy
        order_id = payment.order.id
        order_user_id = payment.order.user_id
        order_total_price = float(payment.order.total_price)
        order_shipping_address = payment.order.shipping_address
        order_items = list(payment.order.items)

        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)
        payment.order.status = "paid"

        await db.commit()

        # Очищаем корзину пользователя после успешной оплаты
        if order_user_id:
            cart_result = await db.execute(select(Cart).where(Cart.user_id == order_user_id))
            cart = cart_result.scalars().first()
            if cart:
                await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
                await db.commit()

        # Отправляем email о подтверждении оплаты (best-effort)
        try:
            user_result = await db.execute(select(User).where(User.id == order_user_id))
            user = user_result.scalars().first()
            if user:
                items_for_email = []
                for oi in order_items:
                    from src.app.models.product import Product

                    prod_result = await db.execute(select(Product).where(Product.id == oi.product_id))
                    prod = prod_result.scalars().first()
                    items_for_email.append(
                        {
                            "product_name": prod.name if prod else "Товар",
                            "quantity": oi.quantity,
                            "price_at_time": float(oi.price_at_time),
                        }
                    )
                await EmailService.send_order_confirmation(
                    to=user.email,
                    order_id=order_id,
                    total_price=order_total_price,
                    items=items_for_email,
                    shipping_address=order_shipping_address,
                )

                await NotificationService.create_notification(
                    db=db,
                    user_id=user.id,
                    type="order_paid",
                    title="Заказ оплачен",
                    message=f"Заказ №{order_id} на сумму {order_total_price:,.0f} ₽ успешно оплачен.",
                    order_id=order_id,
                )
        except Exception:
            logger.exception("Failed to send payment confirmation side-effects")

    @staticmethod
    async def handle_webhook(
        payload: dict,
        raw_body: str | None,
        signature: str | None,
        db: AsyncSession,
    ) -> None:
        """Обработать входящий webhook от ЮKassa."""
        event = payload.get("event", "")
        obj = payload.get("object", {})
        yookassa_payment_id = obj.get("id")

        if not yookassa_payment_id:
            logger.warning("Webhook missing payment id: %s", payload)
            return

        # Validate signature if configured
        if settings.yookassa_webhook_secret and signature and raw_body:
            expected = hmac.new(
                settings.yookassa_webhook_secret.encode(),
                raw_body.encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                logger.warning("Invalid webhook signature for payment %s", yookassa_payment_id)
                return

        # Find payment in DB
        result = await db.execute(
            select(Payment)
            .where(Payment.yookassa_payment_id == yookassa_payment_id)
            .options(selectinload(Payment.order).selectinload(Order.items))
        )
        payment = result.scalars().first()

        if not payment:
            logger.warning("Webhook for unknown payment: %s", yookassa_payment_id)
            return

        yookassa_status = obj.get("status")
        payment.yookassa_status = yookassa_status
        payment.updated_at = datetime.now(timezone.utc)

        if event == "payment.succeeded" or yookassa_status == "succeeded":
            await PaymentService._process_successful_payment(payment, db)
        elif event == "payment.waiting_for_capture" or yookassa_status == "waiting_for_capture":
            # Auto-capture for test shop (self-employed merchant requires manual capture)
            try:
                await YooKassaService.capture_payment(payment.yookassa_payment_id)
                logger.info("Auto-captured payment %s", payment.id)
            except Exception:
                logger.exception("Auto-capture failed for payment %s", payment.id)
            # Process as successful regardless of capture result (best-effort for test env)
            await PaymentService._process_successful_payment(payment, db)
        elif event in ("payment.canceled", "payment.cancelled") or yookassa_status == "canceled":
            payment.status = "cancelled"
            await db.commit()
        else:
            await db.commit()

        logger.info(
            "Processed webhook for payment %s (YooKassa %s): event=%s status=%s",
            payment.id,
            yookassa_payment_id,
            event,
            yookassa_status,
        )

    @staticmethod
    async def sync_payment_status(payment_id: int, user_id: int, db: AsyncSession) -> Payment:
        """Синхронизировать статус платежа с ЮKassa API."""
        result = await db.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.order).selectinload(Order.items))
        )
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.order is None:
            raise HTTPException(status_code=500, detail="Order not loaded for payment")

        if payment.order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        if not payment.yookassa_payment_id:
            raise HTTPException(status_code=400, detail="Payment has no YooKassa ID")

        # Fetch latest status from YooKassa
        logger.debug("Syncing payment %s with YooKassa", payment.yookassa_payment_id)
        yookassa_data = await YooKassaService.get_payment(payment.yookassa_payment_id)
        payment.yookassa_status = yookassa_data["status"]
        payment.updated_at = datetime.now(timezone.utc)

        if yookassa_data["status"] in ("succeeded", "waiting_for_capture") or yookassa_data.get("paid"):
            if yookassa_data["status"] == "waiting_for_capture":
                try:
                    await YooKassaService.capture_payment(payment.yookassa_payment_id)
                except Exception:
                    logger.exception("Manual sync capture failed for payment %s", payment.id)
            await PaymentService._process_successful_payment(payment, db)
        elif yookassa_data["status"] == "canceled":
            payment.status = "cancelled"
            await db.commit()
        else:
            await db.commit()

        await db.refresh(payment)
        return payment

    @staticmethod
    async def sync_payment_status_by_order(order_id: int, user_id: int, db: AsyncSession) -> Payment:
        """Синхронизировать статус платежа по ID заказа."""
        try:
            result = await db.execute(
                select(Payment)
                .where(Payment.order_id == order_id)
                .options(selectinload(Payment.order).selectinload(Order.items))
            )
            payment = result.scalars().first()

            if not payment:
                raise HTTPException(status_code=404, detail="Payment not found for this order")

            if payment.order is None:
                raise HTTPException(status_code=500, detail="Order not loaded for payment")

            if payment.order.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

            if not payment.yookassa_payment_id:
                raise HTTPException(status_code=400, detail="Payment has no YooKassa ID")

            # Fetch latest status from YooKassa
            logger.debug(
                "Syncing payment by order %s (YooKassa %s)",
                order_id,
                payment.yookassa_payment_id,
            )
            yookassa_data = await YooKassaService.get_payment(payment.yookassa_payment_id)
            payment.yookassa_status = yookassa_data["status"]
            payment.updated_at = datetime.now(timezone.utc)

            if yookassa_data["status"] in ("succeeded", "waiting_for_capture") or yookassa_data.get("paid"):
                if yookassa_data["status"] == "waiting_for_capture":
                    try:
                        await YooKassaService.capture_payment(payment.yookassa_payment_id)
                    except Exception:
                        logger.exception("Manual sync capture failed for payment %s", payment.id)
                await PaymentService._process_successful_payment(payment, db)
            elif yookassa_data["status"] == "canceled":
                payment.status = "cancelled"
                await db.commit()
            else:
                await db.commit()

            await db.refresh(payment)
            logger.info(
                "sync_payment_status_by_order: order=%s yookassa_status=%s local_status=%s",
                order_id,
                payment.yookassa_status,
                payment.status,
            )
            return payment
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("sync_payment_status_by_order failed for order %s", order_id)
            raise HTTPException(status_code=500, detail=f"Sync failed: {type(exc).__name__}: {exc}") from exc

    @staticmethod
    async def get_payment(payment_id: int, user_id: int, db: AsyncSession) -> Payment:
        """Получить информацию о платеже (проверяем принадлежность пользователю)."""
        result = await db.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.order))
        )
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return payment

    @staticmethod
    async def cancel_payment(payment_id: int, user_id: int, db: AsyncSession) -> Payment:
        """Отменить платёж (если ещё не оплачен)."""
        result = await db.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.order))
        )
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        if payment.status == "paid":
            raise HTTPException(status_code=400, detail="Cannot cancel paid payment")

        # Try to cancel via YooKassa API if we have a real payment id
        if payment.yookassa_payment_id:
            try:
                await YooKassaService.cancel_payment(payment.yookassa_payment_id)
            except HTTPException as exc:
                # If YooKassa says it's already canceled or cannot cancel, we still update DB
                if exc.status_code != 400:
                    raise
                logger.info(
                    "YooKassa cancel returned %s for payment %s, updating DB anyway",
                    exc.status_code,
                    payment.id,
                )

        payment.status = "cancelled"
        payment.yookassa_status = "canceled"
        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def confirm_mock_payment_by_order(order_id: int, user_id: int, db: AsyncSession) -> Payment:
        """Подтвердить mock-платёж (для dev-режима без реальной YooKassa)."""
        result = await db.execute(
            select(Payment)
            .where(Payment.order_id == order_id)
            .options(selectinload(Payment.order).selectinload(Order.items))
        )
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found for this order")

        if payment.order is None:
            raise HTTPException(status_code=500, detail="Order not loaded for payment")

        if payment.order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        if not payment.yookassa_payment_id or not payment.yookassa_payment_id.startswith("mock-"):
            raise HTTPException(status_code=400, detail="Not a mock payment")

        if payment.status == "paid":
            return payment

        await PaymentService._process_successful_payment(payment, db)
        await db.refresh(payment)
        logger.info("Mock payment confirmed for order %s", order_id)
        return payment
