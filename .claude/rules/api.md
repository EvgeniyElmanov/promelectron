---
description: API route handler conventions
paths:
  - "backend/app/api/**/*.py"
---

# API Route Conventions

- Route handlers must be thin: validate input (Pydantic does it), call one service method, return response
- Never put business logic in route handlers — it belongs in `services/`
- Always use the standard response wrapper from `app/core/responses.py`
- Use `Depends(get_current_user)` for authenticated endpoints
- Use `Depends(get_db)` for DB access — never instantiate sessions manually
- Tag every router for OpenAPI grouping: `router = APIRouter(prefix="/products", tags=["products"])`
- All list endpoints require pagination params via `Depends(PaginationParams)`
