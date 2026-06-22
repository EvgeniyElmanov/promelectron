from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.utils.rate_limiter import conditional_limit

from src.app.db.database import get_db
from src.app.models.supplier import Supplier
from src.app.models.user import User
from src.app.schemas.order import (
    GuestOrderCreate,
    OrderCreate,
    OrderOut,
    OrderUpdateStatus,
    SupplierOrderOut,
    SupplierOrderItemOut,
)
from src.app.services.order_service import OrderService
from src.app.utils.auth import get_current_active_admin, get_current_active_supplier, get_current_active_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/create/", response_model=OrderOut)
@conditional_limit("50/minute")
async def create_order(request: Request,
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an order from the user's cart.
    
    - Gets the current user
    - Transfers items from cart to order
    - Clears the cart after creating the order
    - Returns the created order
    """
    return await OrderService.create_order(current_user=current_user, order_data=order_data, db=db)


@router.post("/create-guest/", response_model=OrderOut)
@conditional_limit("10/minute")
async def create_guest_order(
    request: Request,
    order_data: GuestOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create an order without registration (guest checkout).
    
    - Accepts a list of items with product_id and quantity
    - Validates stock and reduces it
    - Returns the created order
    """
    return await OrderService.create_guest_order(order_data=order_data, db=db)


@router.get("/guest/{order_id}/", response_model=OrderOut)
async def get_guest_order(
    order_id: int,
    guest_email: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a guest order by ID and email."""
    return await OrderService.get_guest_order(order_id=order_id, guest_email=guest_email, db=db)


@router.get("/supplier/", response_model=List[SupplierOrderOut])
async def get_supplier_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    supplier_result = await db.execute(select(Supplier).where(Supplier.user_id == current_user.id))
    supplier = supplier_result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=403, detail="You are not registered as a supplier")

    orders = await OrderService.get_supplier_orders(supplier.id, db, skip=skip, limit=limit)
    return [
        SupplierOrderOut(
            id=order.id,
            buyer_name=order.user.full_name,
            buyer_email=order.user.email,
            total_amount=sum(
                item.price_at_time * item.quantity
                for item in order.items
                if item.product and item.product.supplier_id == supplier.id
            ),
            status=order.status,
            created_at=order.created_at,
            items=[
                SupplierOrderItemOut(
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price_per_item=item.price_at_time,
                )
                for item in order.items
                if item.product and item.product.supplier_id == supplier.id
            ],
        )
        for order in orders
    ]


@router.get("/supplier/{order_id}/", response_model=SupplierOrderOut)
async def get_supplier_order(
    order_id: int,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    supplier_result = await db.execute(select(Supplier).where(Supplier.user_id == current_user.id))
    supplier = supplier_result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=403, detail="You are not registered as a supplier")

    order = await OrderService.get_supplier_order_details(order_id, supplier.id, db)
    return SupplierOrderOut(
        id=order.id,
        buyer_name=order.user.full_name,
        buyer_email=order.user.email,
        total_amount=sum(
            item.price_at_time * item.quantity
            for item in order.items
            if item.product and item.product.supplier_id == supplier.id
        ),
        status=order.status,
        created_at=order.created_at,
        items=[
            SupplierOrderItemOut(
                product_name=item.product.name,
                quantity=item.quantity,
                price_per_item=item.price_at_time,
            )
            for item in order.items
            if item.product and item.product.supplier_id == supplier.id
        ],
    )


@router.patch("/supplier/{order_id}/ship/", response_model=SupplierOrderOut)
async def ship_supplier_order(
    order_id: int,
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    supplier_result = await db.execute(select(Supplier).where(Supplier.user_id == current_user.id))
    supplier = supplier_result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=403, detail="You are not registered as a supplier")

    order = await OrderService.update_supplier_order_status(order_id, supplier.id, "shipped", db)
    return SupplierOrderOut(
        id=order.id,
        buyer_name=order.user.full_name,
        buyer_email=order.user.email,
        total_amount=sum(
            item.price_at_time * item.quantity
            for item in order.items
            if item.product and item.product.supplier_id == supplier.id
        ),
        status=order.status,
        created_at=order.created_at,
        items=[
            SupplierOrderItemOut(
                product_name=item.product.name,
                quantity=item.quantity,
                price_per_item=item.price_at_time,
            )
            for item in order.items
            if item.product and item.product.supplier_id == supplier.id
        ],
    )


@router.get("/{order_id}/", response_model=OrderOut)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService.get_order(order_id=order_id, current_user=current_user, db=db)


@router.get("/", response_model=List[OrderOut])
async def get_orders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService.get_orders(current_user=current_user, db=db)


@router.patch("/{order_id}/cancel/", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Отменить заказ (только если статус pending)."""
    return await OrderService.cancel_order(order_id=order_id, current_user=current_user, db=db)


@router.put("/{order_id}/status/", response_model=OrderOut)
@conditional_limit("10/minute")
async def update_order_status(request: Request,
    order_id: int,
    status_update: OrderUpdateStatus,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService.update_order_status(
        order_id=order_id, status_update=status_update, current_user=current_user, db=db
    )



