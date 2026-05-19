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
2. Create or update Pydantic request/response schemas in `backend/app/schemas/`
3. Implement business logic in `backend/app/services/` — one service class per resource
4. Create or update the route handler in `backend/app/api/v1/` — handler must be thin
5. Register the router in `backend/app/api/v1/router.py` if it's a new file
6. Write tests in `backend/tests/api/` covering:
   - Happy path (201/200 with correct body)
   - Validation errors (422 with field details)
   - Auth required (401 when token missing)
   - Not found (404 when resource doesn't exist)
7. Run `cd backend && uv run pytest tests/api/ -x`
8. Run `cd backend && uv run ruff check app`

Standard response format: `{"data": ..., "meta": null, "error": null}`
List endpoints must paginate using `Depends(PaginationParams)` and include `meta.total`.
