from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.app.models.cart import Cart, CartItem
from server.app.models.order import Order, OrderItem
from server.app.models.product import Product
from server.app.models.user import User
from server.app.schemas.order import AddressDetails, OrderCreate, OrderUpdateStatus


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
            product_result = await db.execute(select(Product).where(Product.id == cart_item.product_id))
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

        new_order = Order(
            user_id=current_user.id,
            total_price=total_price,
            status="pending",
            shipping_address=_format_address(order_data.shipping_address),
            items=order_items,
        )
        db.add(new_order)
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.commit()
        await db.refresh(new_order)

        order_result = await db.execute(
            select(Order).where(Order.id == new_order.id).options(selectinload(Order.items))
        )
        full_order = order_result.scalars().first()
        if not full_order:
            raise HTTPException(status_code=500, detail="Failed to create order")
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
            select(Order).where(Order.user_id == current_user.id).options(selectinload(Order.items))
        )
        return list(result.scalars().all())

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
        return full_order
