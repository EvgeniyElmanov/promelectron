---
description: External integration adapter conventions
paths:
  - "backend/app/integrations/**/*.py"
---

# Integration Conventions

Every integration package must have:
- `client.py` — raw HTTP client, handles auth headers, retry, rate limiting
- `schemas.py` — Pydantic models for the external system's payloads (not app schemas)
- `service.py` — business-logic wrapper; what the rest of the app imports
- `exceptions.py` — integration-specific exception classes

## Active Integrations

| Integration | Purpose | Notes |
|------------|---------|-------|
| 1C (onec) | Product catalog, pricing, stock | **Read-only** — never write to 1C. Sync via Celery beat every 15 min |
| СДЭК | Shipping calculation and tracking | |
| YooKassa | Payment processing | Verify webhook signatures before processing |

## Rules
- Never call `client.py` directly from app services — always go through `service.py`
- Integration clients must handle connection errors and wrap them in domain exceptions
- 1C sync is **read-only** from the app side — never write to 1C
- All outbound payloads logged at DEBUG level, responses at DEBUG level, errors at ERROR level
- Credentials come from `settings` (Pydantic BaseSettings) — never hardcoded
- Payment amounts must be verified server-side — never trust client-provided amounts
