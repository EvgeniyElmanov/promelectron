from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.order import Order, OrderItem
from src.app.models.product import Product
from src.app.models.user import User


class AdminService:
    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> dict:
        """Ключевые метрики для дашборда."""
        # Всего заказов
        orders_count_result = await db.execute(select(func.count(Order.id)))
        total_orders = orders_count_result.scalar() or 0

        # Общая выручка
        revenue_result = await db.execute(select(func.coalesce(func.sum(Order.total_price), Decimal(0))))
        total_revenue = float(revenue_result.scalar() or 0)

        # Всего пользователей
        users_count_result = await db.execute(select(func.count(User.id)))
        total_users = users_count_result.scalar() or 0

        # Всего товаров
        products_count_result = await db.execute(select(func.count(Product.id)))
        total_products = products_count_result.scalar() or 0

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_users": total_users,
            "total_products": total_products,
        }

    @staticmethod
    async def get_orders_by_day(db: AsyncSession, days: int = 7) -> list[dict]:
        """Заказы и выручка за последние N дней (для графика)."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(
                func.date(Order.created_at).label("date"),
                func.count(Order.id).label("orders_count"),
                func.coalesce(func.sum(Order.total_price), Decimal(0)).label("revenue"),
            )
            .where(Order.created_at >= since)
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )

        rows = result.all()
        # Заполняем пропущенные дни нулями
        data = {}
        for row in rows:
            data[str(row.date)] = {
                "date": str(row.date),
                "orders": row.orders_count,
                "revenue": float(row.revenue),
            }

        # Генерируем все дни в диапазоне
        filled = []
        for i in range(days):
            day = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()
            day_str = str(day)
            filled.append(data.get(day_str, {"date": day_str, "orders": 0, "revenue": 0}))

        return filled

    @staticmethod
    async def get_top_products(db: AsyncSession, limit: int = 5) -> list[dict]:
        """Топ товаров по количеству проданных штук."""
        result = await db.execute(
            select(
                Product.id,
                Product.name,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("sold"),
                func.coalesce(func.sum(OrderItem.quantity * OrderItem.price_at_time), Decimal(0)).label("revenue"),
            )
            .join(OrderItem, Product.id == OrderItem.product_id)
            .group_by(Product.id, Product.name)
            .order_by(desc("sold"))
            .limit(limit)
        )

        return [
            {
                "id": row.id,
                "name": row.name,
                "sold": int(row.sold),
                "revenue": float(row.revenue),
            }
            for row in result.all()
        ]

    @staticmethod
    async def get_users_list(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[User]:
        result = await db.execute(
            select(User).order_by(desc(User.created_at)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def toggle_user_active(user_id: int, db: AsyncSession) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = not user.is_active
        await db.commit()
        await db.refresh(user)
        return user
