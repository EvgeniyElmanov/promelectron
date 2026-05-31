---
name: add-endpoint
description: Create a new REST API endpoint with Pydantic schemas, service logic, and tests. Delegates to backend-dev agent.
argument-hint: "<resource and action, e.g. 'products list with category filter'>"
disable-model-invocation: false
context: fork
agent: backend-dev
---

# Add API Endpoint: $ARGUMENTS

Create a new API endpoint for: **$ARGUMENTS**

## Steps

1. Determine the resource, HTTP method, URL path, and auth requirements
2. Create or update Pydantic request/response schemas in `backend/src/app/schemas/`
3. Implement business logic in `backend/src/app/services/` — one service class per resource
4. Create or update the route handler in `backend/src/app/api/` — handler must be thin
5. Register the router in `backend/src/app/main.py` or appropriate router file if it's a new module
6. Write tests in `backend/tests/` covering:
   - Happy path (201/200 with correct body)
   - Validation errors (422 with field details)
   - Auth required (401 when token missing)
   - Not found (404 when resource doesn't exist)
7. Run `cd backend && uv run pytest tests/ -x`
8. Run `cd backend && uv run ruff check src/`

Standard response format: `{"data": ..., "meta": null, "error": null}`
List endpoints must paginate using `Depends(PaginationParams)` and include `meta.total`.
