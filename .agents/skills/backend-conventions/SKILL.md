---
name: backend-conventions
description: Python/FastAPI backend conventions and rules for promelectron. Covers response format, layer architecture, money handling, migrations, integration patterns, and testing.
when_to_use: Load when implementing or reviewing any Python backend code, FastAPI routes, SQLAlchemy models, workers, or integration adapters.
user-invocable: false
paths:
  - "backend/**/*.py"
  - "backend/migrations/**"
---

# Backend Conventions — Promelectron

## Stack
FastAPI + Python 3.12, SQLAlchemy 2 async, Alembic, Pydantic v2, Redis.

## API Response Format
All endpoints return:
```json
{"data": <payload>, "meta": <pagination|null>, "error": null}
{"data": null, "error": {"code": "...", "message": "..."}}
```

## Layer Rules
- **Route handlers** — thin: validate input (Pydantic), call one service method, return response. Zero business logic.
- **Services** — all business logic. Pure functions where possible. Receive db session as parameter.
- **Models** — SQLAlchemy ORM only. No business logic. No raw SQL strings ever.
- **Schemas** — Pydantic v2. Separate request/response schemas. Money fields documented as kopecks.
- **Integrations** — access only via `service.py` wrapper, never `client.py` directly.

## Coding Rules
- `async def` everywhere in routes, services, and integration clients
- Type hints everywhere — mypy strict
- All money as `int` (kopecks) — never float or Decimal
- Soft deletes: `deleted_at: Mapped[datetime | None]` — never hard delete user/order/product data
- UUIDs for user-facing PKs, integer sequences for internal/lookup tables
- Dependency injection via `Depends()` for db session, current_user, settings

## Database
- Every model change → new migration: `alembic revision --autogenerate -m "..."`
- Never edit existing migration files
- Indexes for all FK columns and columns used in WHERE/ORDER BY
- Timestamps: `created_at`, `updated_at` — UTC, auto-managed

## Integration Package Structure
```
integrations/<name>/
  client.py       # httpx.AsyncClient, auth, retry (tenacity), rate limiting
  schemas.py      # Pydantic models for external payloads
  service.py      # Business-logic wrapper — what app code imports
  exceptions.py   # Domain exceptions
```
- 1C (onec) is **read-only** — never write to 1C
- Credentials from `settings` (Pydantic BaseSettings) — never hardcoded

## Testing
- Real test DB via `pytest-asyncio` + `pytest-postgresql` — never mock SQLAlchemy
- External HTTP mocked with `respx`
- Test name: `test_<action>_when_<condition>_should_<result>`
- Run: `cd backend && uv run pytest -x`
