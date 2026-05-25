# P0-1 — Technical Specification

## Architecture Decision: Storage Abstraction

We introduce `StorageService` — an abstraction that hides whether files are stored locally or in MinIO.

```python
from enum import Enum
from typing import Protocol

class StorageBackend(Enum):
    LOCAL = "local"
    MINIO = "minio"

class StorageService(Protocol):
    async def upload(self, key: str, file: UploadFile) -> str:
        """Upload file, return public URL."""
        ...

    def get_url(self, key: str) -> str:
        """Get public URL for existing file."""
        ...

    async def delete(self, key: str) -> None:
        """Delete file by key."""
        ...
```

### Backend Selection Logic

```python
# config.py
minio_endpoint: str | None = os.getenv("MINIO_ENDPOINT")
minio_access_key: str | None = os.getenv("MINIO_ACCESS_KEY")
minio_secret_key: str | None = os.getenv("MINIO_SECRET_KEY")
minio_bucket: str = os.getenv("MINIO_BUCKET", "promelectron-uploads")
minio_secure: bool = os.getenv("MINIO_SECURE", "true").lower() == "true"
```

If all MinIO env vars are set → use MinIO backend.  
Otherwise → fallback to local filesystem (current behavior).

## Tech Stack

| Component | Library | Reason |
|-----------|---------|--------|
| MinIO client | `aiobotocore` | Async, S3-compatible, already familiar to DevOps |
| Alternative | `minio-py` | Official client, but sync-only; would need threadpool |
| Decision | `aiobotocore` | Native async, fits FastAPI async stack |

## Data Model

No schema changes needed. `User.avatar_url` and `ProductImage.image_url` remain `str`.

URL format changes:

| Env | Current | New |
|-----|---------|-----|
| Local | `/uploads/avatars/1/uuid.jpg` | same (fallback) |
| Prod | `https://api.../uploads/avatars/1/uuid.jpg` | `https://minio.../promelectron-uploads/avatars/1/uuid.jpg` |

## API Changes

### `POST /me/avatar`

```python
@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(...):
    # ... validation ...
    key = f"avatars/{current_user.id}/{filename}"
    public_url = await storage.upload(key, file)
    # ... save to DB ...
```

### `POST /products/{id}/images`

Same pattern: compute `key`, call `storage.upload()`, save URL.

### `GET /uploads/avatars/{user_id}/{filename}`

**Option A (chosen): Redirect**
- Keep route registered in FastAPI
- Handler: `return RedirectResponse(url=storage.get_url(key))`
- Returns `307 Temporary Redirect` to MinIO URL
- Frontend/browser follows redirect automatically

**Option B (rejected): Proxy**
- Stream file through API pod
- Wastes bandwidth and CPU
- No benefit over direct MinIO access

**Option C (rejected): Remove route entirely**
- Breaks existing URLs in DB during transition
- Redirect gives graceful migration path

## Bucket Structure

```
promelectron-uploads/
├── avatars/
│   ├── {user_id}/
│   │   └── {uuid}.jpg
├── products/
│   ├── {product_id}/
│   │   └── {uuid}.jpg
```

## Bucket Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::promelectron-uploads/*"]
    }
  ]
}
```

## File Cleanup (Old Avatars)

Current code:
```python
old_path = current_user.avatar_url.lstrip("/")
if os.path.exists(old_path):
    os.remove(old_path)
```

New code:
```python
if current_user.avatar_url:
    key = storage.extract_key_from_url(current_user.avatar_url)
    await storage.delete(key)
```

Need `extract_key_from_url()` method or store `key` separately in DB.  
**Decision:** Parse key from URL. URL pattern is predictable.

## Local Dev Strategy

When `MINIO_ENDPOINT` is not set:
- `LocalStorageService` writes to `uploads/` directory
- `get_url()` returns `/uploads/{key}`
- `StaticFiles(directory="uploads")` stays mounted on `/uploads`
- `docker-compose.yml` stays unchanged

## Migration (Test → Prod)

- **Test env:** Discard existing uploads. No migration script needed.
- **Prod env (future):** One-time script to upload local files to MinIO.

## Testing Strategy

1. **Unit tests:** Mock `StorageService` with `unittest.mock.AsyncMock`
2. **Integration tests:** Use `moto` (mock S3) or local MinIO container
3. **E2E tests:** No changes needed if URLs remain accessible

## Rollback Plan

If MinIO fails in production:
1. Unset `MINIO_ENDPOINT` env var → fallback to local filesystem
2. Re-deploy
3. Files uploaded during MinIO period are inaccessible (acceptable for test env)

## Open Questions

1. Do we need image resizing/thumbnails now, or in P2-4?
   - **Decision:** Postpone to P2-4. MinIO integration should be raw-file-only.
2. Should product images support multiple files per product?
   - **Decision:** Already supported by `products.py`. No change.
3. CDN in front of MinIO?
   - **Decision:** P3-6. Not now.
