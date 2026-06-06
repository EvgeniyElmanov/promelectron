import hashlib
import hmac
import logging
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

        # Проверяем, что платёж ещё не создан
        existing = await db.execute(select(Payment).where(Payment.order_id == order_id))
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Payment already exists for this order")

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

        # Создаём платёж в ЮKassa
        yookassa_result = await YooKassaService.create_payment(
            order_id=order.id,
            amount=order.total_price,
            description=f"Заказ №{order.id}",
            user_id=order.user_id,
            receipt_data=receipt_data,
        )

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

        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)
        payment.order.status = "paid"

        await db.commit()

        # Очищаем корзину пользователя после успешной оплаты
        if payment.order.user_id:
            cart_result = await db.execute(select(Cart).where(Cart.user_id == payment.order.user_id))
            cart = cart_result.scalars().first()
            if cart:
                await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
                await db.commit()

        await db.refresh(payment)

        # Отправляем email о подтверждении оплаты (best-effort)
        try:
            user_result = await db.execute(select(User).where(User.id == payment.order.user_id))
            user = user_result.scalars().first()
            if user:
                items_for_email = []
                for oi in payment.order.items:
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
                    order_id=payment.order.id,
                    total_price=float(payment.order.total_price),
                    items=items_for_email,
                    shipping_address=payment.order.shipping_address,
                )

                await NotificationService.create_notification(
                    db=db,
                    user_id=user.id,
                    type="order_paid",
                    title="Заказ оплачен",
                    message=f"Заказ №{payment.order.id} на сумму {float(payment.order.total_price):,.0f} ₽ успешно оплачен.",
                    order_id=payment.order.id,
                )
        except Exception:
            logger.exception("Failed to send payment confirmation side-effects")

    @staticmethod
    async def handle_webhook(payload: dict, signature: str | None, db: AsyncSession) -> None:
        """Обработать входящий webhook от ЮKassa."""
        event = payload.get("event", "")
        obj = payload.get("object", {})
        yookassa_payment_id = obj.get("id")

        if not yookassa_payment_id:
            logger.warning("Webhook missing payment id: %s", payload)
            return

        # Validate signature if configured
        if settings.yookassa_webhook_secret and signature:
            expected = hmac.new(
                settings.yookassa_webhook_secret.encode(),
                payload.get("raw_body", "").encode(),
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

        if payment.order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        if not payment.yookassa_payment_id:
            raise HTTPException(status_code=400, detail="Payment has no YooKassa ID")

        # Fetch latest status from YooKassa
        yookassa_data = await YooKassaService.get_payment(payment.yookassa_payment_id)
        payment.yookassa_status = yookassa_data["status"]
        payment.updated_at = datetime.now(timezone.utc)

        if yookassa_data["status"] == "succeeded" or yookassa_data.get("paid"):
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
        result = await db.execute(
            select(Payment)
            .where(Payment.order_id == order_id)
            .options(selectinload(Payment.order).selectinload(Order.items))
        )
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found for this order")

        if payment.order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        if not payment.yookassa_payment_id:
            raise HTTPException(status_code=400, detail="Payment has no YooKassa ID")

        # Fetch latest status from YooKassa
        yookassa_data = await YooKassaService.get_payment(payment.yookassa_payment_id)
        payment.yookassa_status = yookassa_data["status"]
        payment.updated_at = datetime.now(timezone.utc)

        if yookassa_data["status"] == "succeeded" or yookassa_data.get("paid"):
            await PaymentService._process_successful_payment(payment, db)
        elif yookassa_data["status"] == "canceled":
            payment.status = "cancelled"
            await db.commit()
        else:
            await db.commit()

        await db.refresh(payment)
        return payment

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
