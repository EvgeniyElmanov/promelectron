---
description: Current infrastructure, deployment topology, and CI/CD pipeline. Read before touching infra/, helm, docker, CI, or anything deployment-related.
---

# Infrastructure Overview

## Status: PRODUCTION-READY

The project is fully deployed, domains are live, CI/CD is green. Do NOT change the infrastructure layout without explicit instruction. When in doubt, ask — don't restructure.

## Deployment Architecture

```
Browser
  └─ HTTPS ──► k8s nginx-ingress (SSL termination)
                 ├─ promelectron-test.aidrivencode.ru  ──► frontend nginx (:80)
                 │     └─ /api/* proxied ──────────────► promelectron-api (:8000)
                 └─ api.promelectron-test.aidrivencode.ru ──► promelectron-api (:8000)
```

- **Prod** namespace: `promelectron` → `promelectron.aidrivencode.ru` / `api.promelectron.aidrivencode.ru`
- **Test** namespace: `promelectron-test` → `promelectron-test.aidrivencode.ru` / `api.promelectron-test.aidrivencode.ru`

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, Redis, Alembic
- Frontend: Vue 3 (Composition API), Vite, Vue Router, Axios, nginx (prod)
- Container registry: Harbor at `harbor.kubeadm.ru/promelectron/`
- Orchestration: Kubernetes + Helm chart (`infra/helm/`)
- Secrets: SOPS-encrypted YAML files
- CI/CD: GitHub Actions (`.github/workflows/deploy.yml`), self-hosted runner

## Repository Layout

```
backend/              Python package: src/app/
  src/app/
    api/              FastAPI routers
    models/           SQLAlchemy models
    schemas/          Pydantic schemas
    services/         Business logic
    db/               Database engine + session
    utils/auth.py     JWT + password utils
  alembic/versions/   DB migrations
  docker-compose.yml  Local: postgres + redis + api
  Dockerfile          Build context: backend/
  docker-entrypoint.sh  Runs seed + uvicorn --proxy-headers

frontend/             Vue 3 SPA
  src/views/          Pages
  src/components/     Components
  src/services/api.js Axios (baseURL: /api/v1 relative)
  nginx.conf          Prod nginx: proxies /api/ to promelectron-api
  e2e/                Playwright tests (global-setup seeds DB)
  docker-compose.yml  Local: frontend only
  Dockerfile          Two-stage: Vite build + nginx

infra/helm/           Kubernetes Helm chart
  templates/          K8s resource templates
  stage/test/         Test env values + secrets
  stage/prod/         Prod env values + secrets
  values.yaml         Defaults (worker.enabled: false)

Makefile              Use make instead of docker compose directly
```

## CI/CD Pipeline

1. **build** — Docker build + push to Harbor
2. **deploy-test** — Helm upgrade to `promelectron-test` namespace
3. **test-smoke** — curl health + frontend check
4. **test-e2e** — Playwright (4 workers, 60s timeout, seeded via globalSetup)
5. **deploy-prod** — workflow_dispatch only

## Frontend API Routing

Frontend uses `API_BASE_URL = '/api/v1'` (relative). nginx proxies `/api/` to the backend k8s service. This means:
- No CORS issues in production (same-origin proxy)
- FastAPI's trailing-slash 307 redirects use `https://` because nginx forwards `X-Forwarded-Proto` from ingress

## Workers

Worker deployment is disabled (`worker.enabled: false`). The queue_worker module does not yet exist.

## E2E

Global setup calls `POST /api/v1/seed` with `x-seed-secret: promelectron-test-seed-2024` to create test users and categories before tests run. No seed step in CI pipeline.

## Local K8s Access

Для работы с кластером требуется:

1. **VPN:** `sudo openvpn --config "/home/evgeniy/Загрузки/khen (1)/khen/khen.ovpn"`
2. **kubectl** + kubeconfig в `~/.kube/config` (chmod 600)
3. **k9s** — TUI альтернатива Lens (`~/.local/bin/k9s`)
4. **Lens** — GUI (устанавливается вручную через .deb)

### Namespace'ы
- Test: `promelectron-test` → `promelectron-test.aidrivencode.ru`
- Prod: `promelectron` → `promelectron.aidrivencode.ru`

### Кластер
- **Context:** `autonoma`
- **Server:** `https://30.30.30.20:6443`
- **Kubeconfig:** `/home/evgeniy/.kube/config`

### Логи
```bash
# Бэкенд
kubectl logs -n promenectron-test -l app=backend --tail=200

# Все поды в namespace
kubectl get pods -n promenectron-test
kubectl describe pod -n promenectron-test <pod>
```
