# PLAN — Promelectron

> Single source of truth for project execution.
> Updated by: `project-manager` agent per `.kimi/rules/planning.md`
> Last updated: 2026-05-13

---

## Current Phase

**Phase 2 — Production Hardening**

Goal: fix blockers that break production before adding new features.

---

## 🚨 P0 — Production Blockers

| ID | Task | Size | Risk | Status | Commit |
|----|------|------|------|--------|--------|
| P0-1 | **[Persistent storage for uploads → .agent/tasks/P0-1-minio/](./.agent/tasks/P0-1-minio/)** | L | high | `[!]` | — |
| | MinIO already deployed in K8s. Task broken into 9 subtasks. See `task.md` + `spec.md` + `progress.md`. | | | | |
| P0-2 | **K8s env: `API_BASE_URL`** | XS | low | `[!]` | — |
| | Add `API_BASE_URL=https://api.promelectron-test.aidrivencode.ru` to `api-deployment.yaml` env. Blocked: infra file is forbidden to assistant. | | | | |
| P0-3 | **Avatar upload end-to-end verify** | S | medium | `[/]` | `d2a6081` |
| | Frontend nginx fix (`^~ /uploads/`) + backend `API_BASE_URL` fallback committed. Need deploy to test and verify JPG/PNG/WebP all work via frontend domain. | | | | |

### P0 Assumptions
- MinIO credentials are in K8s secrets (need verify)
- DevOps will add `API_BASE_URL` env var
- No schema changes needed for S3 migration

---

## 🔶 P1 — High Priority

| ID | Task | Size | Risk | Status | Depends |
|----|------|------|------|--------|---------|
| P1-1 | **CI: unit tests** | M | low | `[ ]` | P0-2 |
| | Add `pytest` and `vitest` stages to `.github/workflows/deploy.yml`. Blocked: workflow file is forbidden. | | | | |
| P1-2 | **WebSocket notifications UI** | M | medium | `[ ]` | — |
| | Backend `ws.py` + `notifications.py` exist. Frontend `Notifications.vue` exists. Need to verify reconnect logic, add toast on order status change. | | | | |
| P1-3 | **OAuth callback flow verify** | S | low | `[ ]` | — |
| | Backend endpoints exist. Check `AuthCallback.vue` handles Google/Yandex tokens correctly. Test on test env. | | | | |
| P1-4 | **Email production (Mailgun)** | S | low | `[ ]` | — |
| | Register domain, get SMTP creds, update K8s secrets. Currently likely Gmail/Mailtrap. | | | | |

---

## 🔸 P2 — Medium Priority

| ID | Task | Size | Risk | Status |
|----|------|------|------|--------|
| P2-1 | **Reviews UI** | M | low | `[ ]` |
| | API `reviews.py` (55 lines) exists. Add `<ProductReviews>` component to `ProductDetail.vue`. | | | |
| P2-2 | **Favorites integration** | S | low | `[ ]` |
| | API `favorites.py` + view `Favorites.vue` exist. Add heart toggle to `ProductCard`, counter in header. | | | |
| P2-3 | **Backend pagination** | M | low | `[ ]` |
| | Add `skip`/`limit` to `/products`, `/orders`, `/admin/users`. Currently may return full dataset. | | | |
| P2-4 | **Image optimization** | M | medium | `[ ]` |
| | Convert uploads to WebP + generate thumbnails via Pillow. Depends on P0-1 (need S3 for multi-size storage). | | | |
| P2-5 | **Redis caching** | M | low | `[ ]` |
| | Cache popular products, categories. Redis already used for rate limiting. | | | |

---

## 🟢 P3 — Tech Debt & Future

| ID | Task | Size | Status |
|----|------|------|--------|
| P3-1 | **Supplier dashboard completeness** | M | `[ ]` |
| | `SupplierProducts.vue` exists. Verify full CRUD + analytics. | | |
| P3-2 | **1C sync monitoring** | S | `[ ]` |
| | Celery task exists. Add metrics, alerts for sync failures. | | |
| P3-3 | **SEO / SSR / Prerender** | L | `[-]` |
| | Dynamic `<title>`, Open Graph, `sitemap.xml`. Nuxt migration or prerender. Deferred until Phase 3. | | |
| P3-4 | **Real payment gateway** | L | `[-]` |
| | Replace mock `PaymentService` with ЮKassa or Stripe. Deferred. | | |
| P3-5 | **Push notifications (FCM)** | L | `[-]` |
| | Firebase Cloud Messaging for mobile/desktop. Deferred. | | |
| P3-6 | **CDN for static assets** | M | `[-]` |
| | CloudFront/CloudFlare for uploads and frontend bundles. Deferred. | | |

---

## 🏁 Completed (Phase 1 — Foundation)

| ID | Task | Commit | Date |
|----|------|--------|------|
| F-1 | FastAPI + PostgreSQL + SQLAlchemy async | — | — |
| F-2 | JWT auth + roles (user/admin/supplier) | — | — |
| F-3 | Vue 3 + Vite + Vue Router | — | — |
| F-4 | Product catalog + categories | — | — |
| F-5 | Cart + checkout + orders | — | — |
| F-6 | Profile + OAuth endpoints + avatar upload | — | — |
| F-7 | Address autocomplete (Nominatim) | — | — |
| F-8 | Email infra + order status emails | — | — |
| F-9 | Admin dashboard (stats, orders, users) | — | — |
| F-10 | Mock payment gateway | — | — |
| S-1 | Security: rate limiting, path traversal fix, stock race fix | `5fc5e5e` | 2026-05-XX |
| S-2 | CI/CD: GitHub Actions → Harbor → K8s Helm | — | — |
| S-3 | E2E tests: Playwright, 92 passed | — | — |
| S-4 | Backend tests: pytest on PostgreSQL, 87 passed | — | — |
| S-5 | Nginx: `client_max_body_size`, `/uploads/` proxy, regex fix | `d2a6081` | 2026-05-13 |

---

## ⚠️ Active Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Uploads lost on pod restart | high | high | P0-1 (MinIO integration) |
| Avatar URL breaks again | medium | medium | P0-2 (API_BASE_URL env) + tests |
| CI deploys untested code | high | medium | P1-1 (unit tests in CI) |
| OAuth flow untested | medium | high | P1-3 (manual E2E verify) |
| Redis not used for caching | medium | low | P2-5 |
| Schema drift without migrations | low | high | Enforce `make migrate` in CI |

---

## 📊 Sprint Proposal — Next 1 Week

**Theme:** Production hardening + verify uploads

**Capacity:** ~5 dev-days

### Must (P0)
- [ ] P0-2: DevOps adds `API_BASE_URL` to K8s
- [ ] P0-3: Deploy and verify avatar upload (JPG/PNG/WebP)

### Should (P1)
- [ ] P1-3: Verify OAuth callback on test env
- [ ] P1-4: Switch SMTP to Mailgun

### Could (P2)
- [ ] P2-2: Favorites heart toggle in catalog

---

## How to Update This File

1. Ask the `project-manager` agent: "Update plan after today's session"
2. Or manually edit, following the task format in `.kimi/rules/planning.md`
3. Always add `(updated: YYYY-MM-DD)` when changing status
