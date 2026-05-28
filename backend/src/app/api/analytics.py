from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.supplier import Supplier
from src.app.models.user import User
from src.app.schemas.analytics import SupplierAnalyticsOut
from src.app.services.analytics_service import AnalyticsService
from src.app.utils.auth import get_current_active_supplier

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/supplier", response_model=SupplierAnalyticsOut)
async def get_supplier_analytics(
    current_user: User = Depends(get_current_active_supplier),
    db: AsyncSession = Depends(get_db),
):
    supplier_result = await db.execute(select(Supplier).where(Supplier.user_id == current_user.id))
    supplier = supplier_result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=403, detail="You are not registered as a supplier")

    kpi = await AnalyticsService.get_supplier_kpi(supplier.id, db)
    orders_by_day = await AnalyticsService.get_supplier_orders_by_day(supplier.id, db, days=30)
    top_products = await AnalyticsService.get_supplier_top_products(supplier.id, db, limit=5)

    return {
        "kpi": kpi,
        "orders_by_day": orders_by_day,
        "top_products": top_products,
    }
