---
description: Testing conventions for backend
paths:
  - "backend/tests/**/*.py"
  - "backend/app/**/*_test.py"
---

# Testing Conventions

- Test file mirrors source: `app/services/product_service.py` → `tests/services/test_product_service.py`
- Test names: `test_<action>_when_<condition>_should_<result>`
- Use real test DB via `pytest-asyncio` + `pytest-postgresql` — never mock the DB layer
- Mock external HTTP calls with `respx` fixtures
- Use fixtures in `conftest.py` for setup — never copy-paste setup code
- One logical assertion per test; if checking multiple fields, group related checks
- Always clean up side effects in teardown or use transaction rollback fixture
- Run `pytest -x` (fail fast) during development, `pytest` (full suite) before commit
