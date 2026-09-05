---
name: testing-conventions
description: Testing conventions for promelectron — backend (pytest, respx, factory_boy) and frontend (Vitest, Playwright E2E). Covers test structure, naming, database strategy, and e-commerce edge cases.
when_to_use: Load when writing, reviewing, or debugging tests for backend or frontend code.
user-invocable: false
paths:
  - "backend/tests/**/*.py"
  - "frontend/src/**/*.test.ts"
  - "frontend/src/**/*.test.tsx"
  - "tests/e2e/**/*.spec.ts"
---

# Testing Conventions — Promelectron

## Backend (pytest)

```
tests/
  api/              # Endpoint tests — real DB, mocked external HTTP
  services/         # Service unit tests — real DB
  integrations/     # Integration adapter tests — mocked HTTP via respx
  conftest.py       # Shared fixtures
```

- **Real PostgreSQL** for all backend tests — never mock SQLAlchemy sessions
- **respx** for mocking external HTTP calls — never let tests hit real APIs
- Rollback DB between tests via transaction fixture in conftest
- `factory_boy` for test data — no hardcoded fixture dicts
- Test naming: `test_<action>_when_<condition>_should_<result>`
- Run: `cd backend && uv run pytest -x -v`

## Frontend (Vitest + Testing Library)

```
frontend/src/__tests__/
  pages/            # Page component tests
  hooks/            # Custom hook tests
  components/       # UI component tests
```

- Mock API calls with `vi.mock` or MSW
- Test user interactions, not implementation details
- Prefer `getByRole`, `getByText` over `getByTestId`
- Run: `cd frontend && npm test`

## E2E (Playwright)

```
tests/e2e/tests/
  api/              # API tests (request context — no browser)
  ui/               # Browser tests (mobile viewport first)
```

- API tests: use `request` fixture, test all status codes and response shape
- UI tests: default to `Pixel 5` viewport (mobile-first)
- Run against test env: `cd tests/e2e && BASE_URL=https://promelectron-test.aidrivencode.ru npx playwright test`

## E-Commerce Edge Cases to Always Test
- Cart race conditions (concurrent add-to-cart for same item)
- Payment idempotency (duplicate webhook delivery)
- Stock overselling (concurrent order creation)
- Price tampering (client-sent amounts must be rejected)
- Object-level auth (user A cannot access user B's orders/cart)
- Pagination edge cases (empty result, single item, last page)
- Soft-deleted items not appearing in listings
