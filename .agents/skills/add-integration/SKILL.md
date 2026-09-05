---
name: add-integration
description: Scaffold a new external system integration with client, schemas, service, exceptions, tests, and documentation. Delegates to backend-dev agent.
argument-hint: "<name and description, e.g. 'stripe payment gateway'>"
disable-model-invocation: false
context: fork
agent: backend-dev
---

# Add Integration: $ARGUMENTS

Scaffold integration with: **$ARGUMENTS**

## Package Structure to Create

```
backend/app/integrations/<name>/
  __init__.py
  client.py        # httpx.AsyncClient, auth, retry (tenacity), rate limiting
  schemas.py       # Pydantic models for external API payloads
  service.py       # Business-logic wrapper — what the rest of app imports
  exceptions.py    # IntegrationError base + specific errors
```

## Steps

1. Read `backend/app/integrations/onec/` as the reference implementation
2. Create all 5 files following the same pattern
3. Add credentials to `backend/app/core/config.py` as Pydantic settings fields
4. Add example env vars to `.env.example` with comments
5. Write tests in `backend/tests/integrations/test_<name>/` using `respx` for HTTP mocking:
   - Successful response
   - Auth failure (401/403)
   - Connection timeout / network error
   - Rate limit response (if applicable)
6. Create integration doc at `docs/integrations/<name>.md` covering:
   - API base URL and auth method
   - Rate limits
   - Endpoints used and why
   - Error codes to handle
7. Run `cd backend && uv run pytest tests/integrations/ -x`

## Rules
- Retry with exponential backoff via `tenacity`
- Never call `client.py` directly from app code — always via `service.py`
- Log requests at DEBUG, responses at DEBUG, errors at ERROR
- Credentials from `settings` — never hardcoded
