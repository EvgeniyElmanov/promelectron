# PLAN — Promelectron

> Single source of truth for project execution.  
> Updated by: `project-manager` agent per `.kimi/rules/planning.md`  
> Last updated: 2026-05-27

---

## Current Phase

**Phase 2 — Production Hardening + Test Stabilization**

Goal: fix blockers that break production, stabilize test suite, and close env gaps before adding new features.

---

## 🚨 P0 — Production Blockers

| ID | Task | Size | Risk | Status | Commit |
|----|------|------|------|--------|--------|
| P0-1 | **[Persistent storage for uploads → .agent/tasks/P0-1-minio/](./.agent/tasks/P0-1-minio/)** | L | high | `[x]` (updated: 2026-05-27) | `e47b2af` |
| | Backend `StorageService` implemented with `aiobotocore` MinIO client + local filesystem fallback. Presigned URLs via `/uploads/{path}` with `307 Redirect`. Bucket auto-creation fixed. All 87 backend tests pass. E2E upload flow verified end-to-end. | | | | |
| P0-2 | **K8s env: `API_BASE_URL`** | XS | low | `[!]` | — |
| | Add `API_BASE_URL=https://api.promelectron-test.aidrivencode.ru` to `api-deployment.yaml` env. Blocked: infra file forbidden to assistant. | | | | |
| P0-3 | **Fix upload test failures (PermissionError)** | S | medium | `[x]` (updated: 2026-05-25) | `5fb553f` |
| | Added `temp_upload_dirs` autouse fixture in `backend/tests/conftest.py` — monkey-patches `UPLOAD_DIR` and `AVATAR_UPLOAD_DIR` to temp directories. Added `cache_dir = "/tmp/pytest-cache-backend"` to `backend/pyproject.toml`. **Result:** 87 passed, 0 failed (was 81/87 with 6 failures). | | | | |

### P0 Infra Fixes (commit `910f61c`)
- **CRITICAL:** Removed `env.open` from `stage/test/values.yaml` and `stage/prod/values.yaml` — Helm replaces maps, not merges.
- **CRITICAL:** Fixed `docker-compose.yml` `depends_on` syntax (invalid `{}` → list format).
- **HIGH:** Removed `curl` healthcheck from minio service (image has no curl).
- **HIGH:** Added `configMapRef` to `minio-deployment.yaml` so MinIO pod reads from ConfigMap.
- Added `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` placeholders to base `values.yaml`.
- Added `ACCESS_TOKEN_EXPIRE_MINUTES` to docker-compose api env.
- Updated `MINIO_INTEGRATION.md` with `env.open` best practice.

### P0 Assumptions
- MinIO credentials exist in K8s secrets (unverified)
- DevOps will add `API_BASE_URL` env var
- No schema changes needed for S3 migration

---

## 🔶 P1 — High Priority

| ID | Task | Size | Risk | Status | Depends |
|----|------|------|------|--------|---------|
| P1-1 | **Stabilize test suite** | M | low | `[x]` (updated: 2026-05-25) | P0-3 |
| | **Backend:** 87/87 passed. **Frontend:** 60/60 passed. All green. Commit: `7335bd0`. | | | | |
| P1-2 | **WebSocket notifications (connect UI)** | M | medium | `[x]` (updated: 2026-05-25) | — |
| | Backend `/ws/notifications` mounted. Frontend `useNotifications.js` uses `new WebSocket` with auto-reconnect + toast. `Header.vue` shows unread badge + dropdown. Fully functional. | | | | |
| P1-3 | **OAuth callback flow verify** | S | low | `[ ]` | — |
| | Backend endpoints exist. `AuthCallback.vue` exists. `.env` has **empty** `GOOGLE_CLIENT_ID` / `YANDEX_CLIENT_ID`. Need real credentials + test on test env. | | | | |
| P1-4 | **Email production (Mailgun)** | S | low | `[ ]` | — |
| | `.env` has empty `SMTP_USER` / `SMTP_PASSWORD`. Currently using Gmail SMTP_HOST for dev. Need Mailgun credentials + K8s secret update. | | | | |
| P1-5 | **Env parity: `.env.example` vs docker-compose** | S | low | `[x]` (updated: 2026-05-27) | — |
| | `.env.example` already contains `REDIS_URL`, `ENVIRONMENT`, `API_BASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`, and all MinIO vars. Verified against `backend/docker-compose.yml`. | | | | |

---

## 🔸 P2 — Medium Priority

| ID | Task | Size | Risk | Status |
|----|------|------|------|--------|
| P2-1 | **Reviews UI** | M | low | `[x]` (updated: 2026-05-25) |
| | `ProductDetail.vue` has full reviews section: `<ProductReviews>` form (rating + text), list with stars, API integration (`POST /reviews/product/{id}`). | | | |
| P2-2 | **Favorites integration (catalog heart)** | S | low | `[x]` (updated: 2026-05-25) |
| | `ProductCard.vue` has heart toggle (`isFavorite`, `toggleFavorite`, calls `/favorites/add/{id}` and `/favorites/remove/{id}`). `Favorites.vue` view works. `Header.vue` and `BottomNav.vue` have nav links. **Minor gap:** no favorites counter badge in header (optional enhancement). | | | |
| P2-3 | **Backend pagination** | M | low | `[x]` (updated: 2026-05-25) |
| | Pagination already implemented: `/products` (20), `/products/my` (100), `/admin/users` (50), `/admin/orders` (50), `/notifications` (50). | | | |
| P2-4 | **Image optimization** | M | medium | `[x]` (updated: 2026-05-27) |
| | Backend `upload_image()` generates WebP variants (small/medium/large). Frontend uses `useImageUrl()` with lazy loading and `srcset`. Commit `8a1d3ac`. | | | |
| P2-5 | **Redis caching** | M | low | `[x]` (updated: 2026-05-27) |
| | `@cache_response` decorator, 5min TTL for products, 1hr for categories, invalidation on CUD. **46x speedup** measured. Commit: `9412962`. | | | |
| P2-6 | **Favorites counter in header** | XS | low | `[x]` (updated: 2026-05-27) |
| | Badge added to `Header.vue` by frontend-dev agent. | | | |

---

## 🟢 P3 — Tech Debt & Future

| ID | Task | Size | Status |
|----|------|------|--------|
| P3-1 | **Celery / 1C sync workers** | M | `[x]` (updated: 2026-05-28) |
| | `.claude/commands/sync-onec.md` references Celery, but no `workers/` or `celery_app.py` found in `backend/src/app/`. Verify if code exists elsewhere or needs creation. | | |
| P3-2 | **Supplier dashboard completeness** | M | `[x]` (updated: 2026-05-27) |
| | Supplier orders API (`GET /orders/supplier/`, `GET /orders/supplier/{id}`, `PATCH /orders/supplier/{id}/ship`). `SupplierOrders.vue` frontend with ship action. `SupplierDashboard.vue` analytics (order counts, revenue, top products). Header nav links for suppliers ("Мои товары", "Мои заказы"). Unit tests: backend 97 passed, frontend 77 passed. Commit: `df2dc3a`. | | |
| P3-3 | **SEO / SSR / Prerender** | L | `[-]` |
| | Dynamic `<title>`, Open Graph, `sitemap.xml`. Deferred until Phase 3. | | |
| P3-4 | **Real payment gateway** | L | `[-]` |
| | Replace mock `PaymentService` with ЮKassa or Stripe. Deferred. | | |
| P3-5 | **Push notifications (FCM)** | L | `[-]` |
| | Firebase Cloud Messaging. Deferred. | | |
| P3-6 | **CDN for static assets** | M | `[-]` |
| | CloudFront/CloudFlare. Deferred. | | |
| P3-7 | **Fix `.pytest_cache` permissions** | XS | `[x]` (updated: 2026-05-25) |
| | Resolved by P0-3: `cache_dir = "/tmp/pytest-cache-backend"` added to `backend/pyproject.toml`. | | |

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
| S-6 | E2E stabilization (Playwright image, Vite allowedHosts, rate limit, workerIndex) | `e253310` | 2026-05-27 |
| P0-3 | Fix upload test failures (PermissionError) | `5fb553f` | 2026-05-25 |
| P1-1 | Stabilize test suite | `7335bd0` | 2026-05-25 |
| P0-1 | Persistent storage for uploads (MinIO) | `e47b2af` | 2026-05-27 |
| P2-4 | Image optimization (WebP + thumbnails) | `8a1d3ac` | 2026-05-27 |
| P2-5 | Redis caching (`@cache_response`, 46x speedup) | `9412962` | 2026-05-27 |
| P3-2 | Supplier dashboard completeness (orders API + frontend + analytics + nav + tests) | `df2dc3a` | 2026-05-27 |

---

## ⚠️ Active Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Uploads lost on pod restart | — | — | **Resolved** — P0-1 complete. MinIO persistent storage + presigned URLs live. |
| Test suite unstable | low | low | **Resolved** — both suites green (backend 87/87, frontend 60/60). Commit: `7335bd0`. |
| Avatar URL breaks again | medium | medium | P0-2 (API_BASE_URL env) |
| CI deploys untested code | medium | medium | Full test suite green; add `npm test` and `pytest` to CI pipeline. |
| Schema drift without migrations | low | high | Enforce `make migrate` in CI |
| Image optimization blocked by S3 dependency | — | — | **Resolved** — P0-1 complete, P2-4 done. WebP variants + thumbnails live. Commit: `8a1d3ac`. |
| Catalog read performance under load | medium | medium | **Resolved** — P2-5 complete. Redis caching with `@cache_response` delivers 46x speedup on product/category endpoints. |
| OAuth untested (no creds) | high | high | P1-3 (get real creds + test) |
| WebSocket notifications silently fail in K8s (no sticky sessions) | medium | low | Verify ingress supports WS upgrade |

---

## 📚 Lessons Learned

| Date | Topic | Lesson |
|------|-------|--------|
| 2026-05-26 | Helm `env.open` | Helm **replaces** maps in values files, it does **not merge** them. Defining `env.open` in a stage `values.yaml` (e.g., `stage/test/values.yaml`) overwrites the entire `env.open` block from base `values.yaml`, dropping all base env vars. **Rule:** always put all env vars in base `values.yaml` and override individual values only, never redefine the whole `env.open` block in stage files. |
| 2026-05-27 | E2E CI failures | `Date.now()` is not unique under parallel workers — always include `test.info().workerIndex`. Rate limiting (`5/minute`) on test env (`ENVIRONMENT=production`) blocks parallel E2E registrations. `serial` mode is a dangerous misdiagnosis for independent tests. |

---

## 📊 Sprint Proposal — Next 1 Week

**Theme:** Background workers + close supplier tooling gaps

**Capacity:** ~3 dev-days

### Must (P0)
- [x] P0-1: Backend MinIO implementation — **done** (commit `e47b2af`)
- [x] P0-3: Fix upload test failures (PermissionError) — **done**
- [x] P1-1: Stabilize test suite — **done** (backend 87/87, frontend 60/60)

### Should (P1)
- [x] P1-5: `.env.example` parity — **done** (verified against docker-compose)
- [ ] P1-3: Get Google/Yandex OAuth creds + test callback — **blocked** (waiting user creds)
- [ ] P1-4: Email production (Mailgun) — **blocked** (waiting Mailgun credentials + K8s secret update)

### Could (P2/P3)
- [x] P2-6: Add favorites counter badge to `Header.vue` — **done**
- [x] P2-4: Image optimization (WebP + thumbnails) — **done** (commit `8a1d3ac`)
- [x] P2-5: Redis caching — **done** (commit `9412962`, 46x speedup)
- [x] P3-2: Supplier dashboard completeness — **done** (commit `df2dc3a`, backend 97/97, frontend 77/77)

### Won't / Deferred
- [ ] P1-3: OAuth callback flow — **blocked** (waiting user creds)
- [ ] P1-4: Mailgun production email — **blocked** (waiting user creds)
- [ ] P0-2: `API_BASE_URL` in K8s — **blocked** (infra file forbidden to assistant)
- [ ] P3-3: SEO / SSR / Prerender — **deferred** (Phase 3)
- [ ] P3-4: Real payment gateway — **deferred** (Phase 3)
- [ ] P3-5: Push notifications (FCM) — **deferred** (Phase 3)
- [ ] P3-6: CDN for static assets — **deferred** (Phase 3)

### Recommended Next Priority
- [x] **P3-1: Celery / 1C sync workers** — **done**. Celery app (`celery_app.py`) + Redis broker, `sync_products_from_onec` task, `OnecClient` HTTP client, `sku` field on Product + migration, beat schedule every 5min. Docker compose services `worker` + `beat`. Tests: 5/5 passed. Full suite: 102/102 passed.

---

## How to Update This File

1. Ask the `project-manager` agent: "Update plan after today's session"
2. Or manually edit, following the task format in `.kimi/rules/planning.md`
3. Always add `(updated: YYYY-MM-DD)` when changing status
