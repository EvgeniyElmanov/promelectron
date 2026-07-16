import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.models.cart import Cart
from src.app.models.cdek_order import CdekOrder
from src.app.models.order import Order, OrderItem
from src.app.models.payment import Payment
from src.app.models.product import Product
from src.app.models.recipient import Recipient
from src.app.models.user import User
from src.app.schemas.order import AdminOrderUpdate, GuestOrderCreate, OrderCreate, OrderUpdateStatus
from src.app.services.cart_service import CartService
from src.app.services.cdek_service import CdekService
from src.app.services.email_service import EmailService
from src.app.services.notification_service import NotificationService
from src.app.services.recipient_service import RecipientService
from src.app.services.yookassa_service import YooKassaService

logger = logging.getLogger(__name__)


class OrderService:
    @staticmethod
    async def _ensure_payment_loaded(order: Order, db: AsyncSession) -> None:
        """Ensure ``order.payment`` is loaded for ``OrderOut.cancellation_reason``.

        ``selectinload(Order.payment)`` is unreliable for one-to-one relationships
        in async SQLAlchemy (it may leave ``order.payment`` as ``None`` even when
        a row exists). If the relationship is not populated, load the payment
        explicitly with a targeted query.
        """
        if order.__dict__.get("payment") is not None:
            return
        result = await db.execute(select(Payment).where(Payment.order_id == order.id))
        order.payment = result.scalars().first()

    @staticmethod
    async def _ensure_payment_loaded_for_orders(orders: list[Order], db: AsyncSession) -> None:
        """Batch-load payments for multiple orders to avoid N+1 queries."""
        missing = [order for order in orders if order.__dict__.get("payment") is None]
        if not missing:
            return

        order_ids = [order.id for order in missing]
        result = await db.execute(select(Payment).where(Payment.order_id.in_(order_ids)))
        payments = {payment.order_id: payment for payment in result.scalars().all()}
        for order in missing:
            order.payment = payments.get(order.id)

    @staticmethod
    async def create_order(current_user: User, order_data: OrderCreate, db: AsyncSession) -> Order:
        cart_result = await db.execute(
            select(Cart).where(Cart.user_id == current_user.id).options(selectinload(Cart.items))
        )
        cart = cart_result.scalars().first()

        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty or does not exist")

        total_price = Decimal(0)
        order_items: list[OrderItem] = []
        ordered_cart_item_ids: list[int] = []
        for cart_item in cart.items:
            product_result = await db.execute(
                select(Product).where(Product.id == cart_item.product_id).with_for_update()
            )
            product = product_result.scalars().first()

            if not product:
                raise HTTPException(status_code=404, detail=f"Product {cart_item.product_id} not found")

            if product.stock < cart_item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for product {product.name}")

            product.stock -= cart_item.quantity
            order_item = OrderItem(
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price_at_time=product.price,
            )
            total_price += Decimal(product.price) * cart_item.quantity
            order_items.append(order_item)
            ordered_cart_item_ids.append(cart_item.id)

        delivery = order_data.cdek_delivery
        delivery_price = delivery.price
        shipping_address = delivery.shipping_address or OrderService._format_shipping_address(delivery)

        recipient = None
        if order_data.recipient_id is not None:
            recipient = await RecipientService.get_for_user(
                user_id=current_user.id,
                recipient_id=order_data.recipient_id,
                db=db,
            )
        else:
            recipient = await RecipientService.create(
                user_id=current_user.id,
                first_name=order_data.recipient_first_name,
                last_name=order_data.recipient_last_name,
                phone=order_data.recipient_phone,
                patronymic=order_data.recipient_patronymic,
                country_code=order_data.recipient_country_code,
                is_default=False,
                db=db,
                commit=False,
            )

        new_order = Order(
            user_id=current_user.id,
            total_price=total_price + delivery_price,
            status="pending",
            shipping_address=shipping_address,
            recipient_id=recipient.id,
            recipient_first_name=recipient.first_name,
            recipient_last_name=recipient.last_name,
            guest_phone=recipient.phone,
            items=order_items,
        )
        db.add(new_order)
        await db.flush()

        cdek_order = CdekOrder(
            order_id=new_order.id,
            tariff_code=delivery.tariff_code,
            delivery_mode=delivery.delivery_mode,
            delivery_point=delivery.delivery_point,
            to_location=delivery.to_location.model_dump() if delivery.to_location else None,
            from_location=delivery.from_location.model_dump() if delivery.from_location else None,
            price=delivery_price,
            period_min=delivery.period_min,
            period_max=delivery.period_max,
        )
        db.add(cdek_order)
        await db.flush()

        new_order.cdek_order_id = cdek_order.id
        await db.commit()
        await db.refresh(new_order)

        if ordered_cart_item_ids:
            await CartService.remove_cart_items_by_ids(
                cart_item_ids=ordered_cart_item_ids,
                db=db,
            )

        order_result = await db.execute(
            select(Order).where(Order.id == new_order.id).options(
                selectinload(Order.items),
                selectinload(Order.payment),
                selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history),
            )
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to create order")

        # Send confirmation email and create notification (best-effort)
        try:
            items_for_email = []
            for oi in full_order.items:
                prod_result = await db.execute(select(Product).where(Product.id == oi.product_id))
                prod = prod_result.scalars().first()
                items_for_email.append({
                    "product_name": prod.name if prod else "Товар",
                    "quantity": oi.quantity,
                    "price_at_time": float(oi.price_at_time),
                })
            await EmailService.send_order_confirmation(
                to=current_user.email,
                order_id=full_order.id,
                total_price=float(full_order.total_price),
                items=items_for_email,
                shipping_address=full_order.shipping_address,
                db=db,
            )

            await NotificationService.create_notification(
                db=db,
                user_id=current_user.id,
                type="order_created",
                title="Заказ оформлен",
                message=f"Ваш заказ №{full_order.id} на сумму {float(full_order.total_price):,.0f} ₽ успешно создан и ожидает оплаты.",
                order_id=full_order.id,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to send order confirmation side-effects")

        await OrderService._ensure_payment_loaded(full_order, db)
        return full_order

    @staticmethod
    async def create_guest_order(order_data: GuestOrderCreate, db: AsyncSession) -> Order:
        if not order_data.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        total_price = Decimal(0)
        order_items: list[OrderItem] = []
        for item in order_data.items:
            product_result = await db.execute(
                select(Product).where(
                    Product.id == item.product_id,
                    Product.is_active.is_(True),
                ).with_for_update()
            )
            product = product_result.scalars().first()

            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

            if product.stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for product {product.name}")

            product.stock -= item.quantity
            order_item = OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_time=product.price,
            )
            total_price += Decimal(product.price) * item.quantity
            order_items.append(order_item)

        delivery = order_data.cdek_delivery
        delivery_price = delivery.price
        shipping_address = delivery.shipping_address or OrderService._format_shipping_address(delivery)

        recipient = Recipient(
            user_id=None,
            first_name=order_data.recipient_first_name,
            last_name=order_data.recipient_last_name,
            patronymic=order_data.recipient_patronymic,
            phone=order_data.recipient_phone,
            country_code=order_data.recipient_country_code,
            is_default=False,
        )
        db.add(recipient)
        await db.flush()

        new_order = Order(
            user_id=None,
            total_price=total_price + delivery_price,
            status="pending",
            shipping_address=shipping_address,
            recipient_id=recipient.id,
            guest_email=order_data.guest_email.lower(),
            guest_phone=recipient.phone,
            recipient_first_name=recipient.first_name,
            recipient_last_name=recipient.last_name,
            save_address=order_data.save_address,
            items=order_items,
        )
        db.add(new_order)
        await db.flush()

        cdek_order = CdekOrder(
            order_id=new_order.id,
            tariff_code=delivery.tariff_code,
            delivery_mode=delivery.delivery_mode,
            delivery_point=delivery.delivery_point,
            to_location=delivery.to_location.model_dump() if delivery.to_location else None,
            from_location=delivery.from_location.model_dump() if delivery.from_location else None,
            price=delivery_price,
            period_min=delivery.period_min,
            period_max=delivery.period_max,
        )
        db.add(cdek_order)
        await db.flush()

        new_order.cdek_order_id = cdek_order.id
        await db.commit()
        await db.refresh(new_order)

        order_result = await db.execute(
            select(Order).where(Order.id == new_order.id).options(
                selectinload(Order.items),
                selectinload(Order.payment),
                selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history),
            )
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to create order")

        # Send confirmation email (best-effort)
        try:
            items_for_email = []
            for oi in full_order.items:
                prod_result = await db.execute(select(Product).where(Product.id == oi.product_id))
                prod = prod_result.scalars().first()
                items_for_email.append({
                    "product_name": prod.name if prod else "Товар",
                    "quantity": oi.quantity,
                    "price_at_time": float(oi.price_at_time),
                })
            await EmailService.send_order_confirmation(
                to=full_order.guest_email,
                order_id=full_order.id,
                total_price=float(full_order.total_price),
                items=items_for_email,
                shipping_address=full_order.shipping_address,
                db=db,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to send order confirmation side-effects")

        await OrderService._ensure_payment_loaded(full_order, db)
        return full_order

    @staticmethod
    def _format_shipping_address(delivery) -> str | None:
        if delivery.delivery_point:
            return f"ПВЗ {delivery.delivery_point}"
        if delivery.to_location and delivery.to_location.address:
            return delivery.to_location.address
        return None

    @staticmethod
    async def get_guest_order(order_id: int, guest_email: str, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(
                Order.id == order_id,
                func.lower(Order.guest_email) == guest_email.lower(),
            )
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
        )
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        await OrderService._ensure_payment_loaded(order, db)
        return order

    @staticmethod
    async def get_all_orders(
        db: AsyncSession, status: str | None = None, user_id: int | None = None, skip: int = 0, limit: int = 50
    ) -> list[Order]:
        from sqlalchemy import select

        query = select(Order).options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
        if status:
            query = query.where(Order.status == status)
        if user_id:
            query = query.where(Order.user_id == user_id)
        query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
        result = await db.execute(query)
        orders = list(result.scalars().all())
        await OrderService._ensure_payment_loaded_for_orders(orders, db)
        return orders

    @staticmethod
    async def get_supplier_orders(supplier_id: int, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Order]:
        subquery = (
            select(Order.id)
            .join(Order.items)
            .join(OrderItem.product)
            .where(Product.supplier_id == supplier_id)
            .distinct()
            .subquery()
        )
        result = await db.execute(
            select(Order)
            .where(Order.id.in_(select(subquery.c.id)))
            .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.recipient), selectinload(Order.user), selectinload(Order.payment))
            .offset(skip)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        orders = list(result.scalars().all())
        await OrderService._ensure_payment_loaded_for_orders(orders, db)
        return orders

    @staticmethod
    async def get_supplier_order_details(order_id: int, supplier_id: int, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.recipient), selectinload(Order.user), selectinload(Order.payment))
        )
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        await OrderService._ensure_payment_loaded(order, db)

        has_supplier_product = any(
            item.product and item.product.supplier_id == supplier_id for item in order.items
        )
        if not has_supplier_product:
            raise HTTPException(status_code=404, detail="Order not found")

        return order

    @staticmethod
    async def update_supplier_order_status(order_id: int, supplier_id: int, new_status: str, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.recipient), selectinload(Order.payment))
        )
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        has_supplier_product = any(
            item.product and item.product.supplier_id == supplier_id for item in order.items
        )
        if not has_supplier_product:
            raise HTTPException(status_code=403, detail="You don't have permission to update this order")

        if new_status != "shipped":
            raise HTTPException(status_code=400, detail="Suppliers can only set status to 'shipped'")

        order.status = new_status
        await db.commit()
        await db.refresh(order)

        # Reload with full relationships for response
        order_result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.recipient), selectinload(Order.user), selectinload(Order.payment))
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to update order")

        await OrderService._ensure_payment_loaded(full_order, db)
        return full_order

    @staticmethod
    async def update_order_by_admin(order_id: int, data: AdminOrderUpdate, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order).where(Order.id == order_id).options(
                selectinload(Order.items),
                selectinload(Order.payment),
                selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history),
            )
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        allowed_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
        status_changed = False

        if data.status is not None:
            if data.status not in allowed_statuses:
                raise HTTPException(status_code=400, detail="Invalid status")
            if order.status != data.status:
                order.status = data.status
                status_changed = True

        if data.tracking_number is not None:
            order.tracking_number = data.tracking_number

        await db.commit()
        await db.refresh(order)

        # Reload order with items for response
        order_result = await db.execute(
            select(Order).where(Order.id == order_id).options(
                selectinload(Order.items),
                selectinload(Order.payment),
                selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history),
            )
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to update order")

        # Send notification if status changed
        if status_changed:
            user_result = await db.execute(select(User).where(User.id == full_order.user_id))
            user = user_result.scalars().first()
            if user:
                try:
                    await EmailService.send_order_status_update(
                        to=user.email,
                        order_id=full_order.id,
                        status=full_order.status,
                        db=db,
                    )

                    status_labels = {
                        "pending": "Ожидает оплаты",
                        "paid": "Оплачен",
                        "shipped": "Отправлен",
                        "delivered": "Доставлен",
                        "cancelled": "Отменён",
                    }
                    label = status_labels.get(full_order.status, full_order.status)
                    await NotificationService.create_notification(
                        db=db,
                        user_id=user.id,
                        type="status_changed",
                        title="Статус заказа изменён",
                        message=f"Заказ №{full_order.id}: {label}",
                        order_id=full_order.id,
                    )
                except Exception:
                    logger.exception("Failed to send status update side-effects for order %s", full_order.id)

        await OrderService._ensure_payment_loaded(full_order, db)
        return full_order

    @staticmethod
    async def get_order(order_id: int, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == current_user.id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        await OrderService._ensure_payment_loaded(order, db)
        return order

    @staticmethod
    async def get_orders(current_user: User, db: AsyncSession) -> list[Order]:
        result = await db.execute(
            select(Order)
            .where(Order.user_id == current_user.id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
        )
        orders = list(result.scalars().all())
        await OrderService._ensure_payment_loaded_for_orders(orders, db)
        return orders

    @staticmethod
    async def cancel_order(order_id: int, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == current_user.id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
            .with_for_update()
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return await OrderService._cancel_order_common(
            order, db, reason="user_cancelled", notify_user_id=current_user.id, notify_email=None
        )

    @staticmethod
    async def cancel_order_by_admin(order_id: int, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
            .with_for_update()
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        notify_email = None
        if order.user_id:
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalars().first()
            notify_email = user.email if user else None
        elif order.guest_email:
            notify_email = order.guest_email

        order = await OrderService._cancel_order_common(
            order, db, reason="admin_cancelled", notify_user_id=order.user_id, notify_email=notify_email
        )
        # Audit trail: отмена может включать refund реальных денег — фиксируем актора (id, не email)
        logger.info("Order %s cancelled by admin user_id=%s", order.id, current_user.id)
        return order

    @staticmethod
    async def _cancel_order_common(
        order: Order,
        db: AsyncSession,
        *,
        reason: str,
        notify_user_id: int | None,
        notify_email: str | None,
    ) -> Order:
        """Общее ядро отмены заказа (user-cancel и admin-cancel).

        Проверка статуса → строгий refund для paid → возврат stock →
        best-effort отмена в CDEK → статус/поля → commit → уведомления.
        Заказ должен быть загружен с selectinload(items/payment/recipient/
        cdek_order.status_history) и заблокирован через SELECT FOR UPDATE.
        """
        if order.status not in ("pending", "paid"):
            raise HTTPException(status_code=400, detail="Order cannot be cancelled")

        if order.status == "paid":
            payment_result = await db.execute(
                select(Payment).where(Payment.order_id == order.id).with_for_update()
            )
            payment = payment_result.scalars().first()

            if not payment:
                raise HTTPException(status_code=400, detail="Payment not found for paid order")

            if payment.status == "refunded":
                raise HTTPException(status_code=400, detail="Order already refunded")

            try:
                await YooKassaService.create_refund(
                    payment.yookassa_payment_id,
                    order.total_price,
                    description=f"Возврат по заказу №{order.id}",
                )
            except HTTPException as exc:
                logger.warning(
                    "Refund failed for order %s, payment %s: %s",
                    order.id,
                    payment.id,
                    exc.detail,
                )
                raise HTTPException(
                    status_code=502,
                    detail="Refund could not be processed. Order was not cancelled.",
                ) from exc
            except Exception as exc:
                logger.exception("Refund failed for order %s, payment %s", order.id, payment.id)
                raise HTTPException(
                    status_code=502,
                    detail="Refund could not be processed. Order was not cancelled.",
                ) from exc

            payment.status = "refunded"
            payment.refunded_amount = order.total_price

        # Return stock
        for item in order.items:
            product_result = await db.execute(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            product = product_result.scalars().first()
            if product:
                product.stock += item.quantity

        order.status = "cancelled"
        order.cancelled_at = datetime.now(timezone.utc)
        order.cancellation_reason = reason

        # Cancel in CDEK (best-effort: CDEK allows deleting only CREATED orders,
        # so a refusal must not block the local cancellation)
        if order.cdek_order and order.cdek_order.cdek_uuid:
            try:
                await CdekService.cancel_cdek_order(order.cdek_order.cdek_uuid)
            except Exception as exc:
                logger.warning(
                    "Failed to cancel CDEK order %s for order %s: %s",
                    order.cdek_order.cdek_uuid,
                    order.id,
                    exc,
                )

        await db.commit()

        # Reload order with items for response
        order_result = await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
        )
        order = order_result.scalars().first()

        # Send notifications (best-effort)
        try:
            if notify_user_id:
                await NotificationService.create_notification(
                    db=db,
                    user_id=notify_user_id,
                    type="order_cancelled",
                    title="Заказ отменён",
                    message=f"Заказ №{order.id} отменён.",
                    order_id=order.id,
                )
            if notify_email:
                await EmailService.send_order_status_update(
                    to=notify_email,
                    order_id=order.id,
                    status="cancelled",
                    db=db,
                )
        except Exception:
            logger.exception("Failed to send order cancellation side-effects for order %s", order.id)

        await OrderService._ensure_payment_loaded(order, db)
        return order

    @staticmethod
    async def ship_order_by_admin(order_id: int, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order))
            .with_for_update()
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "paid":
            raise HTTPException(status_code=400, detail="Only paid orders can be shipped")

        order.status = "shipped"

        if order.cdek_order and order.cdek_order.tracking_number:
            order.tracking_number = order.cdek_order.tracking_number

        await db.commit()

        # Reload order with items for response
        order_result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history))
        )
        order = order_result.scalars().first()

        # Send notification (best-effort)
        try:
            if order.user_id:
                status_labels = {
                    "pending": "Ожидает оплаты",
                    "paid": "Оплачен",
                    "shipped": "Отправлен",
                    "delivered": "Доставлен",
                    "cancelled": "Отменён",
                }
                label = status_labels.get(order.status, order.status)
                await NotificationService.create_notification(
                    db=db,
                    user_id=order.user_id,
                    type="status_changed",
                    title="Статус заказа изменён",
                    message=f"Заказ №{order.id}: {label}",
                    order_id=order.id,
                )
        except Exception:
            logger.exception("Failed to send order shipped notification")

        await OrderService._ensure_payment_loaded(order, db)
        return order

    @staticmethod
    async def update_order_status(
        order_id: int, status_update: OrderUpdateStatus, current_user: User, db: AsyncSession
    ) -> Order:
        result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == current_user.id))
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        allowed_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
        if status_update.status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")

        order.status = status_update.status
        await db.commit()
        await db.refresh(order)

        order_result = await db.execute(
            select(Order).where(Order.id == order_id).options(
                selectinload(Order.items), selectinload(Order.payment), selectinload(Order.recipient), selectinload(Order.cdek_order).selectinload(CdekOrder.status_history)
            )
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to update order")

        # Send status update email
        user_result = await db.execute(select(User).where(User.id == full_order.user_id))
        user = user_result.scalars().first()
        if user:
            try:
                await EmailService.send_order_status_update(
                    to=user.email,
                    order_id=full_order.id,
                    status=full_order.status,
                    db=db,
                )

                status_labels = {
                    "pending": "Ожидает оплаты",
                    "paid": "Оплачен",
                    "shipped": "Отправлен",
                    "delivered": "Доставлен",
                    "cancelled": "Отменён",
                }
                label = status_labels.get(full_order.status, full_order.status)
                await NotificationService.create_notification(
                    db=db,
                    user_id=user.id,
                    type="status_changed",
                    title="Статус заказа изменён",
                    message=f"Заказ №{full_order.id}: {label}",
                    order_id=full_order.id,
                )
            except Exception:
                logger.exception("Failed to send status update side-effects for order %s", full_order.id)

        await OrderService._ensure_payment_loaded(full_order, db)
        return full_order
