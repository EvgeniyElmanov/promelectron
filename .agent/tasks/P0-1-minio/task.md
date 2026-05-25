# P0-1 — Persistent Storage for Uploads via MinIO

> Status: `[planning]` → `ready`  
> Owner: backend-dev  
> Reviewer: code-reviewer  
> Created: 2026-05-13

---

## Problem

Uploaded files (avatars, product images) are stored in the container filesystem (`/app/uploads`). In K8s this is ephemeral — files disappear on every pod restart or redeploy.

MinIO is already deployed in the cluster (`infra/helm/templates/minio-*.yaml`) but not integrated into application code.

## Goal

Store all uploads in MinIO (S3-compatible object storage) instead of local filesystem. Keep local dev working without requiring MinIO.

## Acceptance Criteria

- [ ] Avatar upload (`POST /me/avatar`) writes to MinIO in production, local filesystem in dev
- [ ] Product image upload (`POST /products/{id}/images`) writes to MinIO in production
- [ ] `GET /uploads/avatars/...` and `GET /uploads/products/...` return `307 Redirect` to MinIO public URL (or proxy)
- [ ] Existing files in test env can be discarded (no migration needed)
- [ ] Local dev works without MinIO (fallback to filesystem)
- [ ] All backend tests pass (87)
- [ ] E2E tests pass (92)
- [ ] `PLAN.md` updated: P0-1 marked `[x]`

## Subtasks

| # | Task | Size | Status | Notes |
|---|------|------|--------|-------|
| 1 | **Storage abstraction layer** | S | `[ ]` | `StorageService` with `upload()` and `get_url()` |
| 2 | **Config: MinIO env vars** | XS | `[ ]` | Add to `config.py`, `.env.example` |
| 3 | **MinIO client setup** | S | `[ ]` | `aiobotocore` or `minio-py`, async client |
| 4 | **Migrate avatar upload** | M | `[ ]` | Update `users.py` to use `StorageService` |
| 5 | **Migrate product image upload** | M | `[ ]` | Update `products.py` to use `StorageService` |
| 6 | **Serving files: redirect vs proxy** | S | `[ ]` | Replace `StaticFiles` with redirect handler |
| 7 | **Nginx cleanup** | XS | `[ ]` | Remove `/uploads/` proxy from `frontend/nginx.conf` if serving from MinIO directly |
| 8 | **Tests update** | M | `[ ]` | Mock `StorageService` in tests |
| 9 | **Integration verify on test env** | S | `[ ]` | Deploy, upload avatar, verify URL |

## Dependencies

- `P0-2` (`API_BASE_URL` env) — needed for correct URL generation during transition
- DevOps: MinIO credentials in K8s secrets (assumed existing)

## Blockers

None currently.

## Risks

| Risk | Mitigation |
|------|------------|
| `aiobotocore` conflicts with existing deps | Pin version, test in venv |
| Presigned URL expiration in DB | Use public bucket + direct URL |
| Local dev breaks | Fallback to filesystem when MinIO env not set |
| E2E tests fail due to URL change | Update assertions to match new URL pattern |

## Notes

- MinIO endpoint in K8s: `http://minio:9000` (internal) or `https://minio.promelectron-test.aidrivencode.ru` (external)
- Bucket name: `promelectron-uploads` (suggested)
- Bucket policy: `public-read` for avatars and product images
