# New Database Migration: $ARGUMENTS

Create and validate a migration for: **$ARGUMENTS**

## Steps

1. Make the required model changes in `backend/app/models/`
2. Generate migration:
   ```bash
   cd backend && uv run alembic revision --autogenerate -m "$ARGUMENTS"
   ```
3. Open the generated file in `backend/migrations/versions/` and verify:
   - `upgrade()` does what is expected
   - `downgrade()` correctly reverses it
   - No accidental DROP or data-destroying operations
   - Money columns are `Integer` (never Float)
   - Timestamps are in UTC
4. Apply to dev DB: `cd backend && uv run alembic upgrade head`
5. Run `cd backend && uv run pytest -x` — confirm nothing broke

## Rules
- Never edit existing migration files — create a new one to fix mistakes
- Soft-delete columns: `deleted_at TIMESTAMP WITH TIME ZONE NULL`
- Add explicit indexes for columns used in WHERE clauses
- UUID primary keys for user-facing entities
