from pydantic import BaseModel


class SupplierKPI(BaseModel):
    total_orders: int
    pending_orders: int
    shipped_orders: int
    delivered_orders: int
    total_revenue: float
    total_products: int


class OrdersByDayItem(BaseModel):
    date: str
    count: int


class TopProductItem(BaseModel):
    product_name: str
    total_sold: int
    revenue: float


class SupplierAnalyticsOut(BaseModel):
    kpi: SupplierKPI
    orders_by_day: list[OrdersByDayItem]
    top_products: list[TopProductItem]
