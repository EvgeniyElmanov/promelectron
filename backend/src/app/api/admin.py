from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.admin import (
    AdminUserOut,
    DashboardStats,
    OrdersByDayItem,
    TopProductItem,
)
from src.app.schemas.order import AdminOrderUpdate, OrderOut
from src.app.services.admin_service import AdminService
from src.app.services.order_service import OrderService
from src.app.utils.auth import get_current_active_admin

router = APIRouter()


@router.get("/admin/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService.get_dashboard_stats(db)


@router.get("/admin/orders-by-day", response_model=List[OrdersByDayItem])
async def get_orders_by_day(
    days: int = 7,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService.get_orders_by_day(db, days=days)


@router.get("/admin/top-products", response_model=List[TopProductItem])
async def get_top_products(
    limit: int = 5,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService.get_top_products(db, limit=limit)


@router.get("/admin/users", response_model=List[AdminUserOut])
async def get_users_list(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    users = await AdminService.get_users_list(db, skip=skip, limit=limit)
    return [AdminUserOut.model_validate(u) for u in users]


@router.patch("/admin/users/{user_id}/toggle-active", response_model=AdminUserOut)
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await AdminService.toggle_user_active(user_id, db)
    return AdminUserOut.model_validate(user)


@router.get("/admin/orders", response_model=List[OrderOut])
async def get_admin_orders(
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService.get_all_orders(db, status=status, user_id=user_id, skip=skip, limit=limit)


@router.put("/admin/orders/{order_id}", response_model=OrderOut)
async def update_admin_order(
    order_id: int,
    data: AdminOrderUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    return await OrderService.update_order_by_admin(order_id=order_id, data=data, current_user=current_user, db=db)
