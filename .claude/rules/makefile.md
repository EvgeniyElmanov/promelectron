---
description: How to run the app, tests, and tools locally using Makefile
paths:
  - "Makefile"
  - "backend/docker-compose.yml"
  - "frontend/docker-compose.yml"
---

# Makefile — How Agents Should Run Things

All local dev, test, and tooling commands go through `make`. Never write ad-hoc
`docker run` or `npm` one-liners — use the targets below.

## Start / Stop

```bash
make dev              # Full stack: API + PostgreSQL + Redis + Frontend
make dev-backend      # Only backend (API + DB + Redis)
make dev-frontend     # Only frontend (Vue dev server on :5173)
make stop             # Stop all services
make logs             # Follow all logs
make logs-api         # Follow API logs only
```

## Tests

```bash
make test             # All unit tests (backend pytest + frontend vitest)
make test-backend     # pytest — automatically starts postgres/redis
make test-frontend    # vitest
make test-e2e         # Playwright E2E (starts full stack first)
make test-visual      # Playwright visual smoke (screenshots)
make test-full        # Unit + E2E
```

## Migrations

```bash
make migrate                    # alembic upgrade head
make migrate-down               # alembic downgrade -1
make migrate-generate MSG="..."  # generate new migration
make migrate-history            # show history
make seed                       # load test fixtures
```

## Lint / Format

```bash
make lint             # ruff + oxlint/eslint
make lint-backend     # ruff check src/
make lint-frontend    # npm run lint (in frontend/)
make format           # ruff format + prettier
```

## Build

```bash
make build            # Rebuild all Docker images (no cache)
make build-api
make build-frontend
```

## Key Facts

- Two Docker Compose files: `backend/docker-compose.yml` (postgres + redis + api) and `frontend/docker-compose.yml` (frontend)
- Both share project name `promelectron` so containers can reach each other by service name
- Backend build context: `backend/` — Python package is `src` inside it
- Frontend build context: `frontend/` — Vue 3 + Vite, E2E specs in `frontend/e2e/`
- `make test-backend` runs pytest **inside** a docker compose run container
  (no need to activate a venv locally)
- API is on `http://localhost:8000`, frontend on `http://localhost:5173`
