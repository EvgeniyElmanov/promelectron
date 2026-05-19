---
description: PostgreSQL schema decomposition — which tables live in which schema and why
paths:
  - "backend/app/models/**/*.py"
  - "backend/migrations/**/*.py"
---

# Database Schema Decomposition

Each PostgreSQL schema corresponds to a future microservice boundary.
**Never put a table in `public`.** Every table belongs to a named schema.

## Schema Map

| PG Schema | Future service | Owns |
|-----------|---------------|------|
| `customer` | auth-service | users, user_addresses, user_refresh_tokens |
| `catalog` | catalog-service | products, categories, product_attributes |
| `commerce` | order-service | carts, cart_items, orders, order_items |
| `payment` | payment-service | payments, payment_events |
| `delivery` | delivery-service | deliveries, tracking_events |

## Rules

- Declare schema in every model: `__table_args__ = (..., {"schema": "customer"})`
- Name indexes with schema prefix: `ix_customer_users_email`, `ix_catalog_products_sku`
- **No foreign keys across schemas.** Cross-schema relations are stored as plain UUID columns (no FK constraint). Joins are done in the service layer or via application-level lookups.
  - ✅ `order_items.product_id UUID` — no FK to `catalog.products`
  - ❌ `ForeignKey("catalog.products.id")` — breaks schema isolation

## SQLAlchemy Example

```python
class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_catalog_products_sku", "sku", unique=True),
        {"schema": "catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ...
```

## Migration Checklist

- `CREATE SCHEMA IF NOT EXISTS <name>` in `upgrade()`
- `DROP SCHEMA IF EXISTS <name>` in `downgrade()` only if schema is empty
- Moving existing tables: `ALTER TABLE public.<t> SET SCHEMA <schema>`
- Indexes move with the table but may need renaming: `ALTER INDEX ... RENAME TO ix_<schema>_...`
