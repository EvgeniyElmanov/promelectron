from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.order import OrderCreate, OrderOut, OrderUpdateStatus
from server.app.services.order_service import OrderService
from server.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/create", response_model=OrderOut)
async def create_order(
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


@router.get("/{order_id}", response_model=OrderOut)
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


@router.put("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    status_update: OrderUpdateStatus,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService.update_order_status(
        order_id=order_id, status_update=status_update, current_user=current_user, db=db
    )

