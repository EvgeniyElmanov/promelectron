---
description: Current infrastructure, deployment topology, and CI/CD pipeline. Read before touching infra/, helm, docker, CI, or anything deployment-related.
paths:
  - "infra/**"
  - ".github/workflows/**"
  - "backend/Dockerfile"
  - "frontend/Dockerfile"
  - "frontend/nginx.conf"
  - "backend/docker-compose.yml"
  - "frontend/docker-compose.yml"
  - "Makefile"
---

# Infrastructure Overview

## Status: PRODUCTION-READY

The project is fully deployed, domains are live, CI/CD is green. Do NOT change the infrastructure layout without explicit instruction. When in doubt, ask — don't restructure.

## Deployment Architecture

```
Browser
  └─ HTTPS ──► k8s nginx-ingress (SSL termination)
                 ├─ promelectron-test.aidrivencode.ru  ──► promelectron-frontend (nginx on :80)
                 │     └─ /api/* proxied ──────────────────► promelectron-api (:8000)
                 │     └─ /ws/*  proxied ──────────────────► promelectron-api (:8000)
                 └─ api.promelectron-test.aidrivencode.ru ──► promelectron-api (:8000)
```

- **Prod** namespace: `promelectron`  →  domains: `promelectron.aidrivencode.ru` / `api.promelectron.aidrivencode.ru`
- **Test** namespace: `promelectron-test` → domains: `promelectron-test.aidrivencode.ru` / `api.promelectron-test.aidrivencode.ru`

## Container Registry

Harbor at `harbor.kubeadm.ru/promelectron/`
- API image: `promelectron-api:<sha>`
- Frontend test image: `promelectron-frontend-test:<sha>`
- Frontend prod image: `promelectron-frontend:<sha>`

## Helm Chart

Location: `infra/helm/`
- Stage-specific overrides: `infra/helm/stage/test/values.yaml` and `infra/helm/stage/prod/values.yaml`
- Secrets (SOPS-encrypted): `infra/helm/stage/{test,prod}/secrets.yaml`
- Naming convention: see `.agents/conventions/k8s-naming.md`

## GitHub Actions CI/CD (`deploy.yml`)

Triggered on push to `main` (paths: `backend/**`, `frontend/**`, `infra/helm/**`) or `workflow_dispatch`.

Pipeline:
1. **build** — Docker build+push for API and frontend
2. **deploy-test** — Helm upgrade to `promelectron-test`, waits for rollout
3. **test-smoke** — curl health + frontend reachability
4. **test-e2e** — Playwright tests (4 workers, 60s timeout per test)
5. **deploy-prod** — manual/workflow_dispatch only, requires `environment: production`

## Docker / Local Dev

Compose files are SPLIT by concern:
- `backend/docker-compose.yml` — postgres, redis, api (build context: `backend/`)
- `frontend/docker-compose.yml` — frontend (build context: `frontend/`)
- Both use project name `promelectron` (`-p promelectron`) for shared networking

Use `make` commands — DO NOT call `docker compose` directly:
```
make dev            # full stack
make dev-backend    # just backend
make dev-frontend   # just frontend
make stop / logs / logs-api
```

## Frontend Networking

The frontend container runs nginx (`frontend/nginx.conf`). API calls use relative paths (`/api/v1`) baked at build time via `VITE_API_URL=/api/v1`. nginx proxies:
- `/api/` → `http://promelectron-api:8000/api/`
- `/ws/`  → `http://promelectron-api:8000/ws/`

The nginx config preserves `X-Forwarded-Proto` from the ingress, so FastAPI's trailing-slash redirects use `https://` in production.

## Backend Entry Point

`backend/docker-entrypoint.sh`:
- Seeds test data on startup (idempotent)
- Starts uvicorn with `--proxy-headers --forwarded-allow-ips='*'` so it trusts `X-Forwarded-Proto` from the nginx proxy

## CORS

`CORS_ORIGINS` is read from env var. Helm test values set it to `["https://promelectron-test.aidrivencode.ru"]`. Local dev defaults to localhost:5173. For k8s deployments, API requests go through the frontend nginx proxy (same origin) so CORS isn't needed — the env var matters for direct API access only.

## Workers

Worker deployment (`worker-deployment.yaml`) is disabled via `worker.enabled: false` in `values.yaml`. The worker module (`app.workers.queue_worker`) does not yet exist.

## E2E Tests

- Self-contained: `global-setup.js` calls `/api/v1/seed` before tests run
- Seed secret: `promelectron-test-seed-2024`
- No test data seeding in the CI pipeline itself
