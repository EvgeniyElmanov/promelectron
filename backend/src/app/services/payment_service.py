import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.core.config import settings
from src.app.models.cart import Cart, CartItem
from src.app.models.cdek_order import CdekOrder
from src.app.models.job import Job
from src.app.models.order import Order, OrderItem
from src.app.models.payment import Payment
from src.app.models.user import User
from src.app.schemas.user import UserAddressCreate
from src.app.services.email_service import EmailService
from src.app.services.notification_service import NotificationService
from src.app.services.user_service import UserService
from src.app.services.yookassa_service import YooKassaService

logger = logging.getLogger(__name__)


class PaymentService:
    @staticmethod
    async def _get_existing_payment(order_id: int, db: AsyncSession) -> Payment | None:
        """Найти существующий платёж по order_id или вернуть None."""
        existing_result = await db.execute(select(Payment).where(Payment.order_id == order_id))
        return existing_result.scalars().first()

    @staticmethod
    def _build_receipt_items(order: Order, customer_email: str | None) -> dict | None:
        """Сформировать receipt для 54-FZ (только для обычных ИП/компаний)."""
        if not settings.yookassa_receipt_enabled or not customer_email or not order.items:
            return None
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
        return {
            "customer": {"email": customer_email},
            "items": receipt_items,
            "tax_system_code": settings.yookassa_tax_system_code,
        }

    @staticmethod
    async def _create_or_update_payment(
        order: Order,
        customer_email: str | None,
        yookassa_user_id: int | None,
        db: AsyncSession,
        is_guest: bool = False,
    ) -> Payment:
        """Общая логика создания/обновления платежа для заказа."""
        if order.status != "pending":
            raise HTTPException(status_code=400, detail="Order is not in pending status")

        payment = await PaymentService._get_existing_payment(order.id, db)
        if payment:
            if payment.status == "paid":
                raise HTTPException(status_code=400, detail="Order is already paid")
            payment.status = "pending"

        receipt_data = PaymentService._build_receipt_items(order, customer_email)

        if YooKassaService.is_configured():
            yookassa_result = await YooKassaService.create_payment(
                order_id=order.id,
                amount=order.total_price,
                description=f"Заказ №{order.id}",
                user_id=yookassa_user_id,
                receipt_data=receipt_data,
                guest_email=customer_email if is_guest else None,
            )
        else:
            log_suffix = "guest order" if is_guest else "order"
            logger.info("YooKassa not configured — creating mock payment for %s %s", log_suffix, order.id)
            yookassa_result = {
                "yookassa_payment_id": f"mock-{uuid.uuid4()}",
                "status": "pending",
                "confirmation_url": f"{settings.frontend_url.rstrip('/')}/payment/success?order_id={order.id}&mock=1",
                "amount": order.total_price,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "test": True,
            }

        if payment is None:
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
        else:
            payment.amount = order.total_price
            payment.provider_payment_id = yookassa_result["yookassa_payment_id"]
            payment.yookassa_payment_id = yookassa_result["yookassa_payment_id"]
            payment.yookassa_status = yookassa_result["status"]
            payment.confirmation_url = yookassa_result["confirmation_url"]
            payment.yookassa_created_at = datetime.fromisoformat(
                yookassa_result["created_at"].replace("Z", "+00:00")
            )
            payment.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(payment)
        return payment

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

        customer_email = None
        if order.user and order.user.email:
            customer_email = order.user.email
        elif order.guest_email:
            customer_email = order.guest_email

        return await PaymentService._create_or_update_payment(
            order=order,
            customer_email=customer_email,
            yookassa_user_id=order.user_id,
            db=db,
            is_guest=False,
        )

    @staticmethod
    async def create_guest_payment(order_id: int, guest_email: str, db: AsyncSession) -> Payment:
        """Создать платёж для гостевого заказа через ЮKassa."""
        guest_email = guest_email.lower()
        result = await db.execute(
            select(Order)
            .where(
                Order.id == order_id,
                Order.user_id.is_(None),
                func.lower(Order.guest_email) == guest_email,
            )
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
            )
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return await PaymentService._create_or_update_payment(
            order=order,
            customer_email=order.guest_email,
            yookassa_user_id=None,
            db=db,
            is_guest=True,
        )

    @staticmethod
    def _store_cancellation_details(payment: Payment, details: dict | None) -> None:
        """Persist YooKassa cancellation details inside payment metadata and order.

        We also write the reason directly to ``payment.order.cancellation_reason``
        so ``OrderOut`` exposes it without relying solely on the metadata dict.
        This makes the frontend redirect to ``/payment/failed`` immediately after
        a manual sync, even if the order status is kept ``pending`` for retry.
        """
        if details:
            payment.yookassa_metadata = {
                **(payment.yookassa_metadata or {}),
                "cancellation_details": details,
            }
        reason = (details or {}).get("reason")
        if reason and payment.order is not None:
            payment.order.cancellation_reason = reason

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

        # Автосоздание / привязка пользователя для гостевых заказов
        current_user_id = order_user_id
        if current_user_id is None and payment.order.guest_email:
            try:
                recipient = payment.order.recipient
                user, created, temp_password = await UserService.get_or_create_from_guest(
                    email=payment.order.guest_email,
                    first_name=recipient.first_name if recipient else (payment.order.recipient_first_name or ""),
                    last_name=recipient.last_name if recipient else (payment.order.recipient_last_name or ""),
                    phone=(recipient.phone if recipient else payment.order.guest_phone),
                    db=db,
                    patronymic=recipient.patronymic if recipient else None,
                    country_code=recipient.country_code if recipient else "RU",
                )
                payment.order.user_id = user.id
                current_user_id = user.id

                if created:
                    reset_token = await UserService.create_password_reset_token(
                        user_id=user.id, db=db
                    )
                    await EmailService.send_welcome_email(
                        to=user.email,
                        temp_password=temp_password,
                        reset_token=reset_token,
                        frontend_url=settings.frontend_url,
                        db=db,
                    )
                    logger.info(
                        "Created user from guest checkout: user_id=%s order_id=%s",
                        user.id,
                        order_id,
                    )

                if payment.order.save_address:
                    await PaymentService._save_guest_address(payment.order, user.id, db)
            except Exception:
                logger.exception("Failed to auto-create/link guest user for order %s", order_id)

        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)
        payment.order.status = "paid"

        await db.commit()

        # Очищаем корзину пользователя после успешной оплаты
        if current_user_id:
            cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user_id))
            cart = cart_result.scalars().first()
            if cart:
                await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
                await db.commit()

        # Создаём job для заказа в CDEK (если выбрана CDEK-доставка)
        try:
            cdek_order_result = await db.execute(
                select(CdekOrder).where(CdekOrder.order_id == order_id)
            )
            cdek_order = cdek_order_result.scalars().first()
            if cdek_order and not cdek_order.cdek_uuid:
                db.add(Job(job_type="CDEK_CREATE_ORDER", payload={"order_id": order_id}))
                await db.commit()
                logger.info("Queued CDEK order creation job for order %s", order_id)
        except Exception:
            logger.exception("Failed to queue CDEK order creation for order %s", order_id)

        # Отправляем email о подтверждении оплаты (best-effort)
        try:
            user_result = await db.execute(select(User).where(User.id == current_user_id))
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
                    db=db,
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
    def _parse_address_string(address_str: str, city: str | None) -> tuple[str | None, str | None, str | None]:
        """Извлечь улицу/дом/квартиру из строки адреса, исключая город."""
        if not address_str:
            return None, None, None
        parts = [p.strip() for p in address_str.split(",") if p.strip()]
        if city:
            normalized_city = city.lower().replace("г.", "").replace("город", "").strip()
            if normalized_city:
                parts = [
                    p
                    for p in parts
                    if p.lower().replace("г.", "").replace("город", "").strip() != normalized_city
                ]
        street = parts[0] if len(parts) > 0 else None
        house = parts[1] if len(parts) > 1 else None
        apartment = parts[2] if len(parts) > 2 else None
        return street, house, apartment

    @staticmethod
    async def _save_guest_address(order: Order, user_id: int, db: AsyncSession) -> None:
        """Сохранить адрес доставки гостя в адреса пользователя."""
        city = None
        street = None
        house = None
        apartment = None
        postal_code = None
        cdek_location_code = None
        cdek_delivery_point = None

        cdek_order = order.cdek_order
        if cdek_order:
            cdek_delivery_point = cdek_order.delivery_point
            to_location = cdek_order.to_location
            if isinstance(to_location, dict):
                city = to_location.get("city") or city
                cdek_location_code = to_location.get("code") or cdek_location_code
                postal_code = to_location.get("postal_code") or postal_code
                address_str = to_location.get("address")
                if address_str and isinstance(address_str, str):
                    street, house, apartment = PaymentService._parse_address_string(address_str, city)

        if not city and order.shipping_address:
            shipping = order.shipping_address
            if isinstance(shipping, str):
                street, house, apartment = PaymentService._parse_address_string(shipping, city)
                if not city:
                    city = shipping.split(",")[0].strip() if shipping else None
            elif isinstance(shipping, dict):
                city = shipping.get("city") or city
                street = shipping.get("street") or street
                house = shipping.get("house") or house
                apartment = shipping.get("apartment") or apartment
                postal_code = shipping.get("postal_code") or postal_code

        if not city:
            city = "Не указан"

        address_data = UserAddressCreate(
            label="Адрес доставки",
            city=city,
            street=street,
            house=house,
            apartment=apartment,
            postal_code=postal_code,
            cdek_location_code=cdek_location_code,
            cdek_delivery_point=cdek_delivery_point,
            is_default=True,
        )
        await UserService.save_address(user_id=user_id, address_data=address_data, db=db)

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
            .options(selectinload(Payment.order).selectinload(Order.items), selectinload(Payment.order).selectinload(Order.recipient), selectinload(Payment.order).selectinload(Order.cdek_order))
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
            cancellation_details = obj.get("cancellation_details")
            PaymentService._store_cancellation_details(payment, cancellation_details)
            # Order intentionally remains in "pending" so the user can retry payment
            # from the PaymentFailed page; the UI shows the YooKassa cancellation reason.
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
            .options(selectinload(Payment.order).selectinload(Order.items), selectinload(Payment.order).selectinload(Order.recipient), selectinload(Payment.order).selectinload(Order.cdek_order))
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
            PaymentService._store_cancellation_details(
                payment, yookassa_data.get("cancellation_details")
            )
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
                .options(selectinload(Payment.order).selectinload(Order.items), selectinload(Payment.order).selectinload(Order.recipient), selectinload(Payment.order).selectinload(Order.cdek_order))
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
                PaymentService._store_cancellation_details(
                    payment, yookassa_data.get("cancellation_details")
                )
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
            .options(selectinload(Payment.order).selectinload(Order.items), selectinload(Payment.order).selectinload(Order.recipient), selectinload(Payment.order).selectinload(Order.cdek_order))
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

    @staticmethod
    async def confirm_guest_mock_payment_by_order(
        order_id: int, guest_email: str, db: AsyncSession
    ) -> Payment:
        """Подтвердить mock-платёж для гостевого заказа."""
        result = await db.execute(
            select(Payment)
            .where(Payment.order_id == order_id)
            .options(selectinload(Payment.order).selectinload(Order.items), selectinload(Payment.order).selectinload(Order.recipient), selectinload(Payment.order).selectinload(Order.cdek_order))
        )
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found for this order")

        if payment.order is None:
            raise HTTPException(status_code=500, detail="Order not loaded for payment")

        if payment.order.user_id is not None or payment.order.guest_email.lower() != guest_email.lower():
            raise HTTPException(status_code=404, detail="Order not found")

        if not payment.yookassa_payment_id or not payment.yookassa_payment_id.startswith("mock-"):
            raise HTTPException(status_code=400, detail="Not a mock payment")

        if payment.status == "paid":
            return payment

        await PaymentService._process_successful_payment(payment, db)
        await db.refresh(payment)
        logger.info("Guest mock payment confirmed for order %s", order_id)
        return payment
