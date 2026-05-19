---
description: SQLAlchemy model conventions
paths:
  - "backend/app/models/**/*.py"
  - "backend/migrations/**/*.py"
---

# Database Model Conventions

- All models inherit from `Base` in `app/core/database.py`
- Every model must have `created_at` and `updated_at` columns (auto-managed)
- Use `deleted_at: Mapped[datetime | None]` for soft-deletes on user/order/product tables
- Money columns: `Integer` type, stored in kopecks (multiply/divide by 100 at schema layer)
- UUIDs for user-facing PKs: `id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)`
- After every model change: run `make migration m="descriptive name"`
- Never edit generated migration files — create a new migration to fix issues
- Add indexes explicitly: `__table_args__ = (Index("ix_product_sku", "sku"),)`
