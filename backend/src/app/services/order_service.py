from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.models.cart import Cart
from src.app.models.order import Order, OrderItem
from src.app.models.product import Product
from src.app.models.user import User
from src.app.schemas.order import AdminOrderUpdate, GuestOrderCreate, OrderCreate, OrderUpdateStatus
from src.app.services.email_service import EmailService
from src.app.services.notification_service import NotificationService


class OrderService:
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

        delivery = order_data.cdek_delivery
        delivery_price = delivery.price
        shipping_address = delivery.shipping_address or OrderService._format_shipping_address(delivery)

        new_order = Order(
            user_id=current_user.id,
            total_price=total_price + delivery_price,
            status="pending",
            shipping_address=shipping_address,
            cdek_tariff_code=delivery.tariff_code,
            cdek_delivery_mode=delivery.delivery_mode,
            cdek_delivery_point=delivery.delivery_point,
            cdek_to_location=delivery.to_location.model_dump() if delivery.to_location else None,
            cdek_from_location=delivery.from_location.model_dump() if delivery.from_location else None,
            cdek_price=delivery_price,
            cdek_period_min=delivery.period_min,
            cdek_period_max=delivery.period_max,
            recipient_first_name=order_data.recipient_first_name,
            recipient_last_name=order_data.recipient_last_name,
            items=order_items,
        )
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)

        order_result = await db.execute(
            select(Order).where(Order.id == new_order.id).options(
                selectinload(Order.items),
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

        new_order = Order(
            user_id=None,
            total_price=total_price + delivery_price,
            status="pending",
            shipping_address=shipping_address,
            cdek_tariff_code=delivery.tariff_code,
            cdek_delivery_mode=delivery.delivery_mode,
            cdek_delivery_point=delivery.delivery_point,
            cdek_to_location=delivery.to_location.model_dump() if delivery.to_location else None,
            cdek_from_location=delivery.from_location.model_dump() if delivery.from_location else None,
            cdek_price=delivery_price,
            cdek_period_min=delivery.period_min,
            cdek_period_max=delivery.period_max,
            guest_email=order_data.guest_email.lower(),
            guest_phone=order_data.guest_phone,
            recipient_first_name=order_data.recipient_first_name,
            recipient_last_name=order_data.recipient_last_name,
            save_address=order_data.save_address,
            items=order_items,
        )
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)

        order_result = await db.execute(
            select(Order).where(Order.id == new_order.id).options(
                selectinload(Order.items),
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
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to send order confirmation side-effects")

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
            .options(selectinload(Order.items))
        )
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @staticmethod
    async def get_all_orders(
        db: AsyncSession, status: str | None = None, user_id: int | None = None, skip: int = 0, limit: int = 50
    ) -> list[Order]:
        from sqlalchemy import select

        query = select(Order).options(selectinload(Order.items))
        if status:
            query = query.where(Order.status == status)
        if user_id:
            query = query.where(Order.user_id == user_id)
        query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

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
            .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user))
            .offset(skip)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_supplier_order_details(order_id: int, supplier_id: int, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user))
        )
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        has_supplier_product = any(
            item.product and item.product.supplier_id == supplier_id for item in order.items
        )
        if not has_supplier_product:
            raise HTTPException(status_code=404, detail="Order not found")

        return order

    @staticmethod
    async def update_supplier_order_status(order_id: int, supplier_id: int, new_status: str, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items).selectinload(OrderItem.product))
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
            .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user))
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to update order")

        return full_order

    @staticmethod
    async def update_order_by_admin(order_id: int, data: AdminOrderUpdate, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order).where(Order.id == order_id).options(
                selectinload(Order.items),
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
                await EmailService.send_order_status_update(
                    to=user.email,
                    order_id=full_order.id,
                    status=full_order.status,
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

        return full_order

    @staticmethod
    async def get_order(order_id: int, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == current_user.id)
            .options(selectinload(Order.items))
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @staticmethod
    async def get_orders(current_user: User, db: AsyncSession) -> list[Order]:
        result = await db.execute(
            select(Order)
            .where(Order.user_id == current_user.id)
            .options(selectinload(Order.items))
        )
        return list(result.scalars().all())

    @staticmethod
    async def cancel_order(order_id: int, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == current_user.id)
            .options(selectinload(Order.items))
        )
        order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")

        order.status = "cancelled"

        # Return stock
        for item in order.items:
            product_result = await db.execute(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            product = product_result.scalars().first()
            if product:
                product.stock += item.quantity

        await db.commit()

        # Reload order with items for response
        order_result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        order = order_result.scalars().first()

        # Send notification
        await NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            type="order_cancelled",
            title="Заказ отменён",
            message=f"Заказ №{order.id} отменён.",
            order_id=order.id,
        )

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
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to update order")

        # Send status update email
        user_result = await db.execute(select(User).where(User.id == full_order.user_id))
        user = user_result.scalars().first()
        if user:
            await EmailService.send_order_status_update(
                to=user.email,
                order_id=full_order.id,
                status=full_order.status,
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

        return full_order
