from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from decimal import Decimal
from typing import List

from database import get_db
from models.order import Order, OrderItem
from models.user import User
from models.cart import Cart, CartItem
from models.product import Product
from schemas.order import OrderCreate, OrderUpdateStatus, OrderOut
from utils.auth import get_current_active_user

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/create", response_model=OrderOut)
async def create_order(
    order_: OrderCreate,  # ← Исправлено
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Найдём корзину пользователя + её items
    cart_result = await db.execute(
        select(Cart)
        .where(Cart.user_id == current_user.id)
        .options(selectinload(Cart.items))
    )
    cart = cart_result.scalars().first()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty or does not exist")

    total_price = Decimal(0)

    # Подготовим OrderItems
    order_items = []
    for cart_item in cart.items:
        # Найдём товар и проверим наличие stock
        product_result = await db.execute(
            select(Product).where(Product.id == cart_item.product_id)
        )
        product = product_result.scalars().first()

        if not product:
            raise HTTPException(status_code=404, detail=f"Product {cart_item.product_id} not found")

        if product.stock < cart_item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for product {product.name}")

        # Уменьшим stock
        product.stock -= cart_item.quantity

        # Создадим OrderItem
        order_item = OrderItem(
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price_at_time=product.price  # Цена на момент заказа
        )
        total_price += Decimal(product.price) * cart_item.quantity  # ← Исправлено
        order_items.append(order_item)

    # Создадим Order
    new_order = Order(
        user_id=current_user.id,
        total_price=total_price,
        status="pending",
        items=order_items
    )
    db.add(new_order)

    # Удалим все элементы корзины
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))

    await db.commit()
    await db.refresh(new_order)

    # Загрузим Order с items
    order_result = await db.execute(
        select(Order)
        .where(Order.id == new_order.id)
        .options(selectinload(Order.items))
    )
    full_order = order_result.scalars().first()

    return full_order

@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(selectinload(Order.items))
    )
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order

@router.get("/", response_model=List[OrderOut])
async def get_orders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(selectinload(Order.items))
    )
    orders = result.scalars().all()

    return orders

@router.put("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    status_update: OrderUpdateStatus,  # ← Исправлено
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Проверим, что статус допустим
    allowed_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
    if status_update.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    order.status = status_update.status
    await db.commit()
    await db.refresh(order)

    # Загрузим Order с items
    order_result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    full_order = order_result.scalars().first()

    return full_order