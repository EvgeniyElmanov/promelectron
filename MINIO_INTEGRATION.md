# MinIO Integration Guide — Promelectron

> **For:** Александр (DevOps) + Backend review  
> **Task:** P0-1 — Persistent storage for uploads  
> **Status:** Ready for implementation  
> **Created:** 2026-05-25

---

## 1. Why MinIO?

**Current problem:** Uploaded files (avatars, product images) are stored in the container filesystem (`/app/uploads`). In Kubernetes this is ephemeral — files disappear on every pod restart, redeploy, or node migration.

**Evidence:** Every time the API pod restarts, all user avatars and product images are lost. Users see broken image links.

**Solution:** Use MinIO (already deployed in the cluster) as S3-compatible object storage. Files persist independently of pod lifecycle.

---

## 2. What Already Exists

| Component | File | Status |
|-----------|------|--------|
| MinIO deployment | `infra/helm/templates/minio-deployment.yaml` | ✅ Deployed |
| MinIO PVC | `infra/helm/templates/minio-pvc.yaml` | ✅ Exists |
| MinIO service | `infra/helm/templates/minio-service.yaml` | ✅ Exists |
| Backend upload endpoints | `backend/src/app/api/users.py`, `products.py` | ✅ Work (local fs) |
| StaticFiles mount | `backend/src/app/main.py` | ✅ Serves `/uploads/` |

**What does NOT exist yet:**
- MinIO bucket + public policy
- K8s secrets with MinIO credentials
- `API_BASE_URL` env var
- Backend abstraction layer for storage
- `aiobotocore` dependency

---

## 3. Architecture Overview

```
┌─────────────┐     upload      ┌──────────────┐     S3 API      ┌──────────┐
│   Frontend  │ ───────────────>│   FastAPI    │ ──────────────>│  MinIO   │
│  (browser)  │                 │   (API pod)  │                │ (K8s)    │
└─────────────┘                 └──────────────┘                └──────────┘
       │                                │                              │
       │                                │ 307 Redirect                 │
       │ <──────────────────────────────┼──────────────────────────────┘
       │                                │  (public URL)
       │                                │
       │                         ┌──────┴──────┐
       │                         │   PostgreSQL  │
       │                         │  (avatar_url) │
       │                         └───────────────┘
```

**Flow:**
1. User uploads file → FastAPI receives multipart form
2. FastAPI uploads bytes to MinIO bucket via `aiobotocore`
3. FastAPI stores public MinIO URL in PostgreSQL (`avatar_url`, `image_url`)
4. Browser requests image → FastAPI returns `307 Redirect` to MinIO public URL

---

## 4. Step-by-Step Implementation

### Step 1 — DevOps: K8s Secrets & Bucket (Александр)

#### 1.1 Add env vars to Helm values

In your Helm values file (e.g., `values-test.yaml` or `values-production.yaml`), add to the `env.open` section:

```yaml
env:
  open:
    # Existing vars...
    API_BASE_URL: "https://api.promelectron-test.aidrivencode.ru"
    MINIO_ENDPOINT: "http://promelectron-minio:9000"
    MINIO_BUCKET: "promelectron-uploads"
    MINIO_SECURE: "false"
    ENVIRONMENT: "production"
    REDIS_URL: "redis://promelectron-redis:6379/0"
```

And to `env.secret` (or create separately in `promelectron-secrets`):

```yaml
env:
  secret:
    MINIO_ACCESS_KEY: "<minio-root-user>"
    MINIO_SECRET_KEY: "<minio-root-password>"
```

> **Note:** `API_BASE_URL`, `REDIS_URL`, and `ENVIRONMENT` are also missing. Add them now to avoid separate PRs.

#### 1.2 Create MinIO bucket and policy

Exec into the MinIO pod:

```bash
kubectl exec -it deployment/promelectron-minio -n <namespace> -- sh
```

Inside the pod:

```bash
# Setup mc (MinIO client) pointing to local server
mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Create bucket
mc mb local/promelectron-uploads

# Set public-read policy for avatars and product images
mc anonymous set download local/promelectron-uploads

# Verify
mc anonymous get local/promelectron-uploads
```

**Expected output:** `Access permission for 'local/promelectron-uploads' is 'download'`

#### 1.3 Verify MinIO is reachable from API pod

```bash
kubectl exec -it deployment/promelectron-api -n <namespace> -- sh
# Inside API pod:
curl http://promelectron-minio:9000/minio/health/live
# Expected: 200 OK
```

---

### Step 2 — Backend: Install Dependency

Add to `backend/requirements.txt`:

```
aiobotocore>=2.13.0
```

Then rebuild Docker image or run `pip install aiobotocore` in the pod.

---

### Step 3 — Backend: Config (`backend/src/app/core/config.py`)

Add to the `Settings` dataclass:

```python
    api_base_url: str
    minio_endpoint: str | None
    minio_access_key: str | None
    minio_secret_key: str | None
    minio_bucket: str
    minio_secure: bool
```

Add to the `settings = Settings(...)` instantiation:

```python
    api_base_url=os.getenv("API_BASE_URL", ""),
    minio_endpoint=os.getenv("MINIO_ENDPOINT"),
    minio_access_key=os.getenv("MINIO_ACCESS_KEY"),
    minio_secret_key=os.getenv("MINIO_SECRET_KEY"),
    minio_bucket=os.getenv("MINIO_BUCKET", "promelectron-uploads"),
    minio_secure=os.getenv("MINIO_SECURE", "true").lower() == "true",
```

---

### Step 4 — Backend: Storage Service (`backend/src/app/services/storage_service.py`)

Create new file:

```python
import os
from typing import Protocol

from aiobotocore.session import get_session
from fastapi import UploadFile

from src.app.core.config import settings


class StorageService(Protocol):
    async def upload(self, key: str, file: UploadFile) -> str:
        ...

    def get_url(self, key: str) -> str:
        ...

    async def delete(self, key: str) -> None:
        ...


class LocalStorageService:
    """Fallback for local development without MinIO."""

    async def upload(self, key: str, file: UploadFile) -> str:
        filepath = os.path.join("uploads", key)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
        return f"/uploads/{key}"

    def get_url(self, key: str) -> str:
        return f"/uploads/{key}"

    async def delete(self, key: str) -> None:
        filepath = os.path.join("uploads", key)
        if os.path.exists(filepath):
            os.remove(filepath)


class MinioStorageService:
    """Production storage using MinIO (S3-compatible)."""

    def __init__(self):
        self.endpoint = settings.minio_endpoint
        self.access_key = settings.minio_access_key
        self.secret_key = settings.minio_secret_key
        self.bucket = settings.minio_bucket
        self.secure = settings.minio_secure
        self.session = get_session()

    async def upload(self, key: str, file: UploadFile) -> str:
        async with self.session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.secure,
        ) as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=await file.read(),
                ContentType=file.content_type or "application/octet-stream",
            )
        return self.get_url(key)

    def get_url(self, key: str) -> str:
        # Public bucket — direct URL without presign
        scheme = "https" if self.secure else "http"
        host = self.endpoint.replace("http://", "").replace("https://", "")
        return f"{scheme}://{host}/{self.bucket}/{key}"

    async def delete(self, key: str) -> None:
        async with self.session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.secure,
        ) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)


def get_storage_service() -> StorageService:
    if settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key:
        return MinioStorageService()
    return LocalStorageService()


storage = get_storage_service()
```

---

### Step 5 — Backend: Update Upload Endpoints

#### `backend/src/app/api/users.py`

Replace the upload logic in `upload_avatar`:

```python
from src.app.services.storage_service import storage

# ... inside upload_avatar ...
key = f"avatars/{current_user.id}/{filename}"
public_url = await storage.upload(key, file)

# Delete old avatar if exists
if current_user.avatar_url:
    old_key = current_user.avatar_url.replace(f"{settings.api_base_url}/uploads/", "").lstrip("/")
    if old_key and not old_key.startswith("http"):
        await storage.delete(old_key)

return await UserService.update_profile(
    user_id=current_user.id,
    user_data=UserUpdate(avatar_url=public_url),
    db=db,
)
```

Remove the `base_url = settings.api_base_url or str(request.base_url).rstrip("/")` line.

#### `backend/src/app/api/products.py`

Similarly, replace file saving logic in image upload endpoint:

```python
from src.app.services.storage_service import storage

# ... inside upload_image ...
key = f"products/{product_id}/{filename}"
public_url = await storage.upload(key, file)
```

Update `image_url` storage in DB to use `public_url`.

---

### Step 6 — Backend: Serving Files (`backend/src/app/main.py`)

Replace the `StaticFiles` mount with a redirect handler:

```python
from fastapi import Request
from fastapi.responses import RedirectResponse, FileResponse

from src.app.services.storage_service import storage

# Remove or conditionally disable:
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/uploads/{path:path}")
async def serve_upload(request: Request, path: str):
    url = storage.get_url(path)
    if url.startswith("/"):
        # Local dev — fallback to filesystem
        filepath = os.path.join("uploads", path)
        if os.path.exists(filepath):
            return FileResponse(filepath)
        raise HTTPException(status_code=404, detail="File not found")
    return RedirectResponse(url=url, status_code=307)
```

---

### Step 7 — Frontend: Nginx Cleanup (`frontend/nginx.conf`)

Remove or comment out the `/uploads/` location since files are now served directly from MinIO (or via API redirect):

```nginx
# REMOVED — uploads now served directly from MinIO
# location ^~ /uploads/ {
#     proxy_pass http://promelectron-api:8000/uploads/;
# }
```

---

### Step 8 — Docker Compose (Local Dev)

Add to `backend/docker-compose.yml`:

```yaml
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

volumes:
  minio_data:
```

And add to the `api` service environment:

```yaml
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      MINIO_BUCKET: promelectron-uploads
      MINIO_SECURE: "false"
      API_BASE_URL: http://localhost:8000
      ENVIRONMENT: development
      REDIS_URL: redis://redis:6379/0
```

---

### Step 9 — Tests Update

Update `backend/tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def mock_storage_service(monkeypatch):
    from src.app.services import storage_service
    class FakeStorage:
        async def upload(self, key, file):
            return f"https://minio.example.com/bucket/{key}"
        def get_url(self, key):
            return f"https://minio.example.com/bucket/{key}"
        async def delete(self, key):
            pass
    monkeypatch.setattr(storage_service, "storage", FakeStorage())
```

Remove or update the old `temp_upload_dirs` fixture since `upload()` is now mocked entirely.

---

### Step 10 — `.env.example` Update

Add to `backend/.env.example`:

```env
# --- MinIO (S3-compatible storage) ---
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=promelectron-uploads
MINIO_SECURE=false

# --- Base URL ---
API_BASE_URL=http://localhost:8000

# --- Environment ---
ENVIRONMENT=development

# --- Redis ---
REDIS_URL=redis://redis:6379/0
```

---

## 5. Rollback Plan

If something goes wrong:

1. Unset `MINIO_ENDPOINT` in K8s → backend falls back to `LocalStorageService`
2. Restore `frontend/nginx.conf` `/uploads/` proxy location
3. Re-enable `StaticFiles` mount in `main.py`
4. Files uploaded during MinIO period will have external URLs — they become 404, but new uploads go to local fs again (acceptable for test env)

---

## 6. Verification Checklist

After deployment:

- [ ] `kubectl get pods` — MinIO pod Running
- [ ] `mc ls local/promelectron-uploads` — bucket exists
- [ ] Upload avatar via frontend → `avatar_url` in DB starts with `https://minio...`
- [ ] `curl -I <avatar_url>` → returns `200 OK` directly from MinIO
- [ ] `pytest backend/tests/` → 87 passed
- [ ] E2E tests → 92 passed

---

## 7. Files Changed Summary

| File | Action | Owner |
|------|--------|-------|
| Helm values (`values-*.yaml`) | Add env vars | Александр |
| K8s secrets | Add MinIO creds | Александр |
| MinIO pod | Create bucket + policy | Александр |
| `backend/requirements.txt` | Add `aiobotocore` | Backend dev |
| `backend/src/app/core/config.py` | Add MinIO settings | Backend dev |
| `backend/src/app/services/storage_service.py` | **New file** — storage abstraction | Backend dev |
| `backend/src/app/api/users.py` | Use `storage.upload()` | Backend dev |
| `backend/src/app/api/products.py` | Use `storage.upload()` | Backend dev |
| `backend/src/app/main.py` | Replace StaticFiles with redirect | Backend dev |
| `frontend/nginx.conf` | Remove `/uploads/` proxy | Frontend dev |
| `backend/docker-compose.yml` | Add MinIO service | Александр |
| `backend/tests/conftest.py` | Mock storage service | Backend dev |
| `backend/.env.example` | Add all missing vars | Backend dev |
