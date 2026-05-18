from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.app.models.order import Order, OrderItem
from server.app.models.payment import Payment
from server.app.models.user import User
from server.app.services.email_service import EmailService
from server.app.services.notification_service import NotificationService


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
        await db.refresh(payment)

        # Отправляем email о подтверждении оплаты
        user_result = await db.execute(select(User).where(User.id == payment.order.user_id))
        user = user_result.scalars().first()
        if user:
            items_for_email = []
            for oi in payment.order.items:
                from server.app.models.product import Product
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
