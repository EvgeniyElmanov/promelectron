# PLAN — Promelectron

> Single source of truth for project execution.  
> Updated by: `project-manager` agent per `.kimi/rules/planning.md`  
> Last updated: 2026-05-13

---

## Current Phase

**Phase 2 — Production Hardening + Test Stabilization**

Goal: fix blockers that break production, stabilize test suite, and close env gaps before adding new features.

---

## 🚨 P0 — Production Blockers

| ID | Task | Size | Risk | Status | Commit |
|----|------|------|------|--------|--------|
| P0-1 | **[Persistent storage for uploads → .agent/tasks/P0-1-minio/](./.agent/tasks/P0-1-minio/)** | L | high | `[!]` | — |
| | MinIO deployed in K8s but not in docker-compose. Files ephemeral in containers. See `task.md` + `spec.md` + `progress.md`. | | | | |
| P0-2 | **K8s env: `API_BASE_URL`** | XS | low | `[!]` | — |
| | Add `API_BASE_URL=https://api.promelectron-test.aidrivencode.ru` to `api-deployment.yaml` env. Blocked: infra file forbidden to assistant. | | | | |
| P0-3 | **Fix test: `test_upload_product_image`** | S | medium | `[!]` | — |
| | `PermissionError: [Errno 13] Permission denied: 'uploads/products/1/...'`. Directory likely owned by root (created inside Docker). Need `chown` or volume mount fix. | | | | |

### P0 Assumptions
- MinIO credentials exist in K8s secrets (unverified)
- DevOps will add `API_BASE_URL` env var
- No schema changes needed for S3 migration

---

## 🔶 P1 — High Priority

| ID | Task | Size | Risk | Status | Depends |
|----|------|------|------|--------|---------|
| P1-1 | **Stabilize test suite** | M | low | `[/]` | P0-3 |
| | **Backend:** 74/75 passed. 1 failed: `test_upload_product_image` (PermissionError). **Frontend:** 59/60 passed. 1 failed: `Admin.spec.js` (text assertion broken by layout change). | | | | |
| P1-2 | **WebSocket notifications (connect UI)** | M | medium | `[ ]` | — |
| | Backend `ws.py` + `notifications.py` exist. `Notifications.vue` uses REST polling only. No WebSocket connection in frontend. Need to add `new WebSocket(wsUrl)` in `Notifications.vue` or `App.vue`. | | | | |
| P1-3 | **OAuth callback flow verify** | S | low | `[ ]` | — |
| | Backend endpoints exist. `AuthCallback.vue` exists. `.env` has **empty** `GOOGLE_CLIENT_ID` / `YANDEX_CLIENT_ID`. Need real credentials + test on test env. | | | | |
| P1-4 | **Email production (Mailgun)** | S | low | `[ ]` | — |
| | `.env` has empty `SMTP_USER` / `SMTP_PASSWORD`. Currently using Gmail SMTP_HOST for dev. Need Mailgun credentials + K8s secret update. | | | | |
| P1-5 | **Env parity: `.env.example` vs docker-compose** | S | low | `[ ]` | — |
| | `.env.example` missing: `REDIS_URL`, `ENVIRONMENT`, `API_BASE_URL`. Docker-compose sets them, but `.env.example` does not document them. | | | | |

---

## 🔸 P2 — Medium Priority

| ID | Task | Size | Risk | Status |
|----|------|------|------|--------|
| P2-1 | **Reviews UI** | M | low | `[ ]` |
| | API `reviews.py` exists (POST/GET/PUT/DELETE). **No `<ProductReviews>` component** on `ProductDetail.vue`. | | | |
| P2-2 | **Favorites integration (catalog heart)** | S | low | `[ ]` |
| | API `favorites.py` + view `Favorites.vue` exist. **No heart toggle** on `ProductCard`. No favorites counter in header. | | | |
| P2-3 | **Backend pagination** | M | low | `[ ]` |
| | Add `skip`/`limit` to `/products`, `/orders`, `/admin/users`. Currently likely returns full dataset. | | | |
| P2-4 | **Image optimization** | M | medium | `[ ]` |
| | Convert uploads to WebP + thumbnails. Depends on P0-1 (need S3 for multi-size). | | | |
| P2-5 | **Redis caching** | M | low | `[ ]` |
| | Cache popular products, categories. Redis already used for rate limiting. | | | |

---

## 🟢 P3 — Tech Debt & Future

| ID | Task | Size | Status |
|----|------|------|--------|
| P3-1 | **Celery / 1C sync workers** | M | `[ ]` |
| | `.claude/commands/sync-onec.md` references Celery, but no `workers/` or `celery_app.py` found in `backend/src/app/`. Verify if code exists elsewhere or needs creation. | | |
| P3-2 | **Supplier dashboard completeness** | M | `[ ]` |
| | `SupplierProducts.vue` exists. Verify full CRUD + analytics. | | |
| P3-3 | **SEO / SSR / Prerender** | L | `[-]` |
| | Dynamic `<title>`, Open Graph, `sitemap.xml`. Deferred until Phase 3. | | |
| P3-4 | **Real payment gateway** | L | `[-]` |
| | Replace mock `PaymentService` with ЮKassa or Stripe. Deferred. | | |
| P3-5 | **Push notifications (FCM)** | L | `[-]` |
| | Firebase Cloud Messaging. Deferred. | | |
| P3-6 | **CDN for static assets** | M | `[-]` |
| | CloudFront/CloudFlare. Deferred. | | |

---

## 🏁 Completed (Phase 1 — Foundation)

| ID | Task | Commit | Date |
|----|------|--------|------|
| F-1 | FastAPI + PostgreSQL + SQLAlchemy async | — | — |
| F-2 | JWT auth + roles (user/admin/supplier) | — | — |
| F-3 | Vue 3 + Vite + Vue Router (15 views) | — | — |
| F-4 | Product catalog + categories | — | — |
| F-5 | Cart + checkout + orders | — | — |
| F-6 | Profile + OAuth endpoints + avatar upload | — | — |
| F-7 | Address autocomplete (Nominatim) | — | — |
| F-8 | Email infra + order status emails | — | — |
| F-9 | Admin dashboard (stats, orders, users) | — | — |
| F-10 | Mock payment gateway | — | — |
| F-11 | Notifications API + view | — | — |
| F-12 | Reviews API + favorites API | — | — |
| F-13 | WebSocket backend (`/ws/notifications`) | — | — |
| S-1 | Security: rate limiting, path traversal fix, stock race fix | `5fc5e5e` | — |
| S-2 | CI/CD: GitHub Actions → Harbor → K8s Helm | — | — |
| S-3 | E2E tests: Playwright, 92 passed | — | — |
| S-4 | Nginx: `client_max_body_size`, `/uploads/` proxy, regex fix | `d2a6081` | 2026-05-13 |
| S-5 | Plan system: `project-manager` agent, `PLAN.md`, `.agent/tasks/` | `635bc09` | 2026-05-13 |

---

## ⚠️ Active Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Uploads lost on pod restart | high | high | P0-1 (MinIO integration) |
| Test suite unstable (1 backend + 1 frontend failure) | high | medium | P1-1 (fix tests) |
| Avatar URL breaks again | medium | medium | P0-2 (API_BASE_URL env) |
| CI deploys untested code | high | medium | P1-1 (stabilize + add to CI) |
| WebSocket backend unused | high | low | P1-2 (connect frontend) |
| Reviews/favorites API orphaned | medium | low | P2-1, P2-2 (add UI) |
| Schema drift without migrations | low | high | Enforce `make migrate` in CI |
| OAuth untested (no creds) | high | high | P1-3 (get real creds + test) |

---

## 📊 Sprint Proposal — Next 1 Week

**Theme:** Stabilize tests + close env gaps

**Capacity:** ~4 dev-days

### Must (P0)
- [ ] P0-3: Fix `test_upload_product_image` (chown uploads/ or mock storage)
- [ ] P0-2: DevOps adds `API_BASE_URL` to K8s

### Should (P1)
- [ ] P1-1: Fix `Admin.spec.js` (update selector or assertion)
- [ ] P1-5: Update `.env.example` with all required vars (`REDIS_URL`, `ENVIRONMENT`, `API_BASE_URL`)
- [ ] P1-3: Get Google/Yandex OAuth creds + test callback

### Could (P2)
- [ ] P2-2: Add heart toggle to `ProductCard`

---

## How to Update This File

1. Ask the `project-manager` agent: "Update plan after today's session"
2. Or manually edit, following the task format in `.kimi/rules/planning.md`
3. Always add `(updated: YYYY-MM-DD)` when changing status
