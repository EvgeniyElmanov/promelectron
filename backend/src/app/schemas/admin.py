from pydantic import BaseModel, ConfigDict


class DashboardStats(BaseModel):
    total_orders: int
    total_revenue: float
    total_users: int
    total_products: int


class OrdersByDayItem(BaseModel):
    date: str
    orders: int
    revenue: float


class TopProductItem(BaseModel):
    id: int
    name: str
    sold: int
    revenue: float


class AdminUserOut(BaseModel):
    id: int
    full_name: str | None
    email: str
    role: str
    is_active: bool
    created_at: str | None = None
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj):
        data = {
            "id": obj.id,
            "full_name": obj.full_name,
            "email": obj.email,
            "role": obj.role.value if hasattr(obj.role, "value") else str(obj.role),
            "is_active": obj.is_active,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
        return cls(**data)


class FeatureFlagOut(BaseModel):
    name: str
    enabled: bool
    env_default: bool | None
    redis_override: bool | None
    source: str


class FeatureFlagUpdate(BaseModel):
    enabled: bool
