from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.models.cart import Cart, CartItem
from src.app.models.delivery_method import DeliveryMethod
from src.app.models.order import Order, OrderItem
from src.app.models.product import Product
from src.app.models.user import User
from src.app.schemas.order import AddressDetails, AdminOrderUpdate, OrderCreate, OrderUpdateStatus
from src.app.services.email_service import EmailService
from src.app.services.notification_service import NotificationService


def _format_address(address: AddressDetails | None) -> str | None:
    if not address:
        return None
    parts = []
    if address.region:
        parts.append(f"обл. {address.region}")
    if address.district:
        parts.append(f"р-н {address.district}")
    if address.city:
        parts.append(address.city)
    if address.street:
        parts.append(f"ул. {address.street}")
    if address.house:
        parts.append(f"д. {address.house}")
    if address.apartment:
        parts.append(f"кв. {address.apartment}")
    return ", ".join(parts) if parts else None


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

        delivery_price = Decimal(0)
        if order_data.delivery_method_id:
            dm_result = await db.execute(
                select(DeliveryMethod).where(
                    DeliveryMethod.id == order_data.delivery_method_id,
                    DeliveryMethod.is_active.is_(True),
                )
            )
            dm = dm_result.scalars().first()
            if dm:
                delivery_price = Decimal(dm.base_price)

        new_order = Order(
            user_id=current_user.id,
            total_price=total_price + delivery_price,
            status="pending",
            delivery_method_id=order_data.delivery_method_id,
            delivery_price=delivery_price,
            shipping_address=_format_address(order_data.shipping_address),
            items=order_items,
        )
        db.add(new_order)
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.commit()
        await db.refresh(new_order)

        order_result = await db.execute(
            select(Order).where(Order.id == new_order.id).options(
                selectinload(Order.items),
                selectinload(Order.delivery_method),
            )
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to create order")

        # Send confirmation email
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

        # Create notification
        await NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            type="order_created",
            title="Заказ оформлен",
            message=f"Ваш заказ №{full_order.id} на сумму {float(full_order.total_price):,.0f} ₽ успешно создан и ожидает оплаты.",
            order_id=full_order.id,
        )

        return full_order

    @staticmethod
    async def get_all_orders(
        db: AsyncSession, status: str | None = None, user_id: int | None = None, skip: int = 0, limit: int = 50
    ) -> list[Order]:
        from sqlalchemy import select

        query = select(Order).options(selectinload(Order.items), selectinload(Order.delivery_method))
        if status:
            query = query.where(Order.status == status)
        if user_id:
            query = query.where(Order.user_id == user_id)
        query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_order_by_admin(order_id: int, data: AdminOrderUpdate, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order).where(Order.id == order_id).options(
                selectinload(Order.items),
                selectinload(Order.delivery_method),
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
                selectinload(Order.delivery_method),
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
            .options(selectinload(Order.items), selectinload(Order.delivery_method))
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
            .options(selectinload(Order.items), selectinload(Order.delivery_method))
        )
        return list(result.scalars().all())

    @staticmethod
    async def cancel_order(order_id: int, current_user: User, db: AsyncSession) -> Order:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == current_user.id)
            .options(selectinload(Order.items), selectinload(Order.delivery_method))
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
            .options(selectinload(Order.items), selectinload(Order.delivery_method))
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
