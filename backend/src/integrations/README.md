# Ozon Collector

Standalone service that pulls data from Ozon Seller API and stores it in ClickHouse.

## What it collects

| Entity | Schedule | Endpoint |
|--------|----------|----------|
| Products | Every 4h | /v3/product/list + /v3/product/info/list |
| Orders (FBO+FBS) | Every 30min | /v2/posting/fbo/list, /v3/posting/fbs/list |
| Transactions | Daily 03:00 | /v3/finance/transaction/list |
| Stocks | Every 4h | /v2/analytics/stock_on_warehouses |
| Prices | Every 4h | /v5/product/info/prices |
| Analytics | Daily 04:00 | /v1/analytics/data |
| Product queries | Daily 05:00 | /v1/analytics/product-queries |
| Categories | Daily 02:00 | /v1/description-category/tree |

## Setup

```bash
cp .env.example .env
# fill in .env values
uv sync
uv run collector --help
```

## Usage

```bash
# Start scheduler (runs forever)
uv run collector

# One-time full sync on startup, then start scheduler
uv run collector --full-sync

# Full sync for specific entities only
uv run collector --full-sync --entities products,orders

# Full sync since a date
uv run collector --full-sync --since 2024-01-01
```

## ClickHouse migrations

Migrations are applied automatically on startup. SQL files are in `migrations/`.

## See also

- `docs/integrations/ozon.md` — Ozon API reference (rate limits, pagination patterns, gotchas)
