from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.models.cart import Cart, CartItem
from src.app.models.order import Order
from src.app.models.payment import Payment
from src.app.models.user import User
from src.app.services.email_service import EmailService
from src.app.services.notification_service import NotificationService


class PaymentService:
    @staticmethod
    async def create_payment(order_id: int, user_id: int, db: AsyncSession) -> Payment:
        """Создать платёж для заказа."""
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(selectinload(Order.items))
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

        payment = Payment(
            order_id=order.id,
            amount=order.total_price,
            status="pending",
            provider_payment_id=f"mock_{order_id}_{int(datetime.now(timezone.utc).timestamp())}",
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return payment

    @staticmethod
    async def confirm_payment(payment_id: int, db: AsyncSession) -> Payment:
        """Подтвердить платёж (mock callback от платёжного шлюза)."""
        result = await db.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.order).selectinload(Order.items))
        )
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.status == "paid":
            raise HTTPException(status_code=400, detail="Payment already paid")

        if payment.status == "cancelled":
            raise HTTPException(status_code=400, detail="Payment is cancelled")

        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)

        # Обновляем статус заказа
        payment.order.status = "paid"

        await db.commit()

        # Очищаем корзину пользователя после успешной оплаты
        if payment.order.user_id:
            cart_result = await db.execute(select(Cart).where(Cart.user_id == payment.order.user_id))
            cart = cart_result.scalars().first()
            if cart:
                from sqlalchemy import delete
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
                    items_for_email.append({
                        "product_name": prod.name if prod else "Товар",
                        "quantity": oi.quantity,
                        "price_at_time": float(oi.price_at_time),
                    })
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
            import logging
            logging.getLogger(__name__).exception("Failed to send payment confirmation side-effects")

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

        payment.status = "cancelled"
        await db.commit()
        await db.refresh(payment)
        return payment
