from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.order import Order, OrderItem
from src.app.models.product import Product


class AnalyticsService:
    @staticmethod
    async def get_supplier_revenue(supplier_id: int, db: AsyncSession, days: int = 30) -> float:
        """Sum of OrderItem.price_at_time * OrderItem.quantity for delivered/shipped orders in last N days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(func.coalesce(func.sum(OrderItem.price_at_time * OrderItem.quantity), Decimal(0)))
            .join(OrderItem.order)
            .join(OrderItem.product)
            .where(
                Product.supplier_id == supplier_id,
                Order.status.in_(["delivered", "shipped"]),
                Order.created_at >= since,
            )
        )
        return float(result.scalar() or 0)

    @staticmethod
    async def get_supplier_orders_by_day(supplier_id: int, db: AsyncSession, days: int = 30) -> list[dict]:
        """Count of distinct orders per day containing supplier's products."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Subquery of distinct order IDs containing supplier products
        subq = (
            select(Order.id)
            .join(Order.items)
            .join(OrderItem.product)
            .where(Product.supplier_id == supplier_id)
            .distinct()
            .subquery()
        )

        result = await db.execute(
            select(
                func.date(Order.created_at).label("date"),
                func.count(Order.id).label("orders_count"),
            )
            .where(
                Order.id.in_(select(subq.c.id)),
                Order.created_at >= since,
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )

        rows = result.all()
        data = {}
        for row in rows:
            data[str(row.date)] = {
                "date": str(row.date),
                "count": row.orders_count,
            }

        # Fill missing days with zeros
        filled = []
        for i in range(days):
            day = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()
            day_str = str(day)
            filled.append(data.get(day_str, {"date": day_str, "count": 0}))

        return filled

    @staticmethod
    async def get_supplier_top_products(supplier_id: int, db: AsyncSession, limit: int = 5) -> list[dict]:
        """Top products by total quantity sold (delivered/shipped orders only)."""
        result = await db.execute(
            select(
                Product.name,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("total_sold"),
                func.coalesce(func.sum(OrderItem.price_at_time * OrderItem.quantity), Decimal(0)).label("revenue"),
            )
            .join(OrderItem, Product.id == OrderItem.product_id)
            .join(OrderItem.order)
            .where(
                Product.supplier_id == supplier_id,
                Order.status.in_(["delivered", "shipped"]),
            )
            .group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )

        return [
            {
                "product_name": row.name,
                "total_sold": int(row.total_sold),
                "revenue": float(row.revenue),
            }
            for row in result.all()
        ]

    @staticmethod
    async def get_supplier_kpi(supplier_id: int, db: AsyncSession) -> dict:
        """Key supplier metrics."""
        # Subquery of distinct order IDs containing supplier products
        subq = (
            select(Order.id)
            .join(Order.items)
            .join(OrderItem.product)
            .where(Product.supplier_id == supplier_id)
            .distinct()
            .subquery()
        )

        total_orders_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.id.in_(select(subq.c.id)))
        )
        total_orders = total_orders_result.scalar() or 0

        pending_orders_result = await db.execute(
            select(func.count(Order.id))
            .where(
                Order.id.in_(select(subq.c.id)),
                Order.status == "pending",
            )
        )
        pending_orders = pending_orders_result.scalar() or 0

        shipped_orders_result = await db.execute(
            select(func.count(Order.id))
            .where(
                Order.id.in_(select(subq.c.id)),
                Order.status == "shipped",
            )
        )
        shipped_orders = shipped_orders_result.scalar() or 0

        delivered_orders_result = await db.execute(
            select(func.count(Order.id))
            .where(
                Order.id.in_(select(subq.c.id)),
                Order.status == "delivered",
            )
        )
        delivered_orders = delivered_orders_result.scalar() or 0

        revenue_result = await db.execute(
            select(func.coalesce(func.sum(OrderItem.price_at_time * OrderItem.quantity), Decimal(0)))
            .join(OrderItem.order)
            .join(OrderItem.product)
            .where(
                Product.supplier_id == supplier_id,
                Order.status.in_(["delivered", "shipped"]),
            )
        )
        total_revenue = float(revenue_result.scalar() or 0)

        products_result = await db.execute(
            select(func.count(Product.id))
            .where(Product.supplier_id == supplier_id)
        )
        total_products = products_result.scalar() or 0

        return {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "shipped_orders": shipped_orders,
            "delivered_orders": delivered_orders,
            "total_revenue": total_revenue,
            "total_products": total_products,
        }
