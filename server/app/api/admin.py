from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.admin import (
    AdminUserOut,
    DashboardStats,
    OrdersByDayItem,
    TopProductItem,
)
from server.app.services.admin_service import AdminService
from server.app.utils.auth import get_current_active_admin

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
