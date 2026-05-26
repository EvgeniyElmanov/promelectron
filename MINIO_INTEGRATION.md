# Руководство по интеграции MinIO — Promelectron

> **Для:** Александра (DevOps) + Backend-разработчика  
> **Задача:** P0-1 — Постоянное хранилище для загружаемых файлов  
> **Статус:** Готово к реализации  
> **Создано:** 2026-05-25

---

## 1. Зачем нужен MinIO?

**Текущая проблема:** Загружаемые файлы (аватары, фото товаров) хранятся в файловой системе контейнера (`/app/uploads`). В Kubernetes это эфемерное хранилище — файлы исчезают при каждом перезапуске, редеплое или миграции пода.

**Последствия:** При каждом рестарте API-пода пропадают все аватарки пользователей и фото товаров. Пользователи видят битые ссылки на изображения.

**Решение:** Использовать MinIO (уже развёрнут в кластере) как S3-совместимое объектное хранилище. Файлы сохраняются независимо от жизненного цикла подов.

---

## 2. Что уже существует

| Компонент | Файл | Статус |
|-----------|------|--------|
| Деплоймент MinIO | `infra/helm/templates/minio-deployment.yaml` | ✅ Развёрнут |
| PVC MinIO | `infra/helm/templates/minio-pvc.yaml` | ✅ Существует |
| Сервис MinIO | `infra/helm/templates/minio-service.yaml` | ✅ Существует |
| Endpoint'ы загрузки | `backend/src/app/api/users.py`, `products.py` | ✅ Работают (локальная ФС) |
| Раздача статики | `backend/src/app/main.py` | ✅ Монтирует `/uploads/` |

**Что ещё НЕ существует:**
- Бакет MinIO + публичная политика
- K8s-секреты с учётными данными MinIO
- Переменная окружения `API_BASE_URL`
- Абстракция хранилища в бэкенде
- Зависимость `aiobotocore`

---

## 3. Общая архитектура

```
┌─────────────┐     загрузка    ┌──────────────┐     S3 API      ┌──────────┐
│   Фронтенд  │ ───────────────>│   FastAPI    │ ──────────────>│  MinIO   │
│  (браузер)  │                 │   (API pod)  │                │ (K8s)    │
└─────────────┘                 └──────────────┘                └──────────┘
       │                                │                              │
       │                                │ 307 Redirect                 │
       │ <──────────────────────────────┼──────────────────────────────┘
       │                                │  (публичный URL)
       │                                │
       │                         ┌──────┴──────┐
       │                         │   PostgreSQL  │
       │                         │  (avatar_url) │
       │                         └───────────────┘
```

**Поток данных:**
1. Пользователь загружает файл → FastAPI получает multipart-форму
2. FastAPI загружает байты в бакет MinIO через `aiobotocore`
3. FastAPI сохраняет публичный URL MinIO в PostgreSQL (`avatar_url`, `image_url`)
4. Браузер запрашивает изображение → FastAPI возвращает `307 Redirect` на публичный URL MinIO

---

## 4. Пошаговая реализация

### Шаг 1 — DevOps: K8s-секреты и бакет (Александр)

#### 1.1 Добавить переменные окружения в Helm values / ConfigMap

В файле Helm values (например, `values-test.yaml` или `values-production.yaml`), добавить в секцию `env.open` (ConfigMap):

```yaml
env:
  open:
    # Существующие переменные...
    API_BASE_URL: "https://api.promelectron-test.aidrivencode.ru"
    MINIO_ENDPOINT: "http://promelectron-minio:9000"
    MINIO_BUCKET: "promelectron-uploads"
    MINIO_SECURE: "false"
    ENVIRONMENT: "production"
    REDIS_URL: "redis://promelectron-redis:6379/0"
    # --- Временно в открытом виде (переделаем на Secret позже) ---
    MINIO_ACCESS_KEY: "<minio-root-user>"
    MINIO_SECRET_KEY: "<minio-root-password>"
```

> **Примечание:** Александр создаёт пароли, но не редактирует файлы. Evgeniy прописывает creds в ConfigMap.  
> **Временное решение:** Creds в открытом виде в ConfigMap, чтобы не тормозить разработку. Переделаем на K8s Secret после запуска.

#### 1.2 Создать бакет MinIO и политику доступа

Подключиться к поду MinIO:

```bash
kubectl exec -it deployment/promelectron-minio -n <namespace> -- sh
```

Внутри пода:

```bash
# Настроить mc (клиент MinIO) на локальный сервер
mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Создать бакет
mc mb local/promelectron-uploads

# Установить публичную политику чтения для аватаров и фото товаров
mc anonymous set download local/promelectron-uploads

# Проверить
mc anonymous get local/promelectron-uploads
```

**Ожидаемый результат:** `Access permission for 'local/promelectron-uploads' is 'download'`

#### 1.3 Проверить доступность MinIO из API-пода

```bash
kubectl exec -it deployment/promelectron-api -n <namespace> -- sh
# Внутри API-пода:
curl http://promelectron-minio:9000/minio/health/live
# Ожидается: 200 OK
```

---

### Шаг 2 — Бэкенд: Установка зависимости

Добавить в `backend/requirements.txt`:

```
aiobotocore>=2.13.0
```

Затем пересобрать Docker-образ или запустить `pip install aiobotocore` в поде.

---

### Шаг 3 — Бэкенд: Конфигурация (`backend/src/app/core/config.py`)

Добавить в датакласс `Settings`:

```python
    api_base_url: str
    minio_endpoint: str | None
    minio_access_key: str | None
    minio_secret_key: str | None
    minio_bucket: str
    minio_secure: bool
```

Добавить в инстанциацию `settings = Settings(...)`:

```python
    api_base_url=os.getenv("API_BASE_URL", ""),
    minio_endpoint=os.getenv("MINIO_ENDPOINT"),
    minio_access_key=os.getenv("MINIO_ACCESS_KEY"),
    minio_secret_key=os.getenv("MINIO_SECRET_KEY"),
    minio_bucket=os.getenv("MINIO_BUCKET", "promelectron-uploads"),
    minio_secure=os.getenv("MINIO_SECURE", "true").lower() == "true",
```

---

### Шаг 4 — Бэкенд: Сервис хранилища (`backend/src/app/services/storage_service.py`)

Создать новый файл:

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
    """Fallback для локальной разработки без MinIO."""

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
    """Продакшен-хранилище через MinIO (S3-совместимый)."""

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
        # Публичный бакет — прямой URL без подписи
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

### Шаг 5 — Бэкенд: Обновить endpoint'ы загрузки

#### `backend/src/app/api/users.py`

Заменить логику загрузки в `upload_avatar`:

```python
from src.app.services.storage_service import storage

# ... внутри upload_avatar ...
key = f"avatars/{current_user.id}/{filename}"
public_url = await storage.upload(key, file)

# Удалить старый аватар, если есть
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

Удалить строку `base_url = settings.api_base_url or str(request.base_url).rstrip("/")`.

#### `backend/src/app/api/products.py`

Аналогично заменить сохранение файла в endpoint загрузки изображений:

```python
from src.app.services.storage_service import storage

# ... внутри upload_image ...
key = f"products/{product_id}/{filename}"
public_url = await storage.upload(key, file)
```

Обновить сохранение `image_url` в БД на `public_url`.

---

### Шаг 6 — Бэкенд: Раздача файлов (`backend/src/app/main.py`)

Заменить монтирование `StaticFiles` на обработчик редиректа:

```python
from fastapi import Request
from fastapi.responses import RedirectResponse, FileResponse

from src.app.services.storage_service import storage

# Удалить или условно отключить:
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/uploads/{path:path}")
async def serve_upload(request: Request, path: str):
    url = storage.get_url(path)
    if url.startswith("/"):
        # Локальная разработка — fallback на файловую систему
        filepath = os.path.join("uploads", path)
        if os.path.exists(filepath):
            return FileResponse(filepath)
        raise HTTPException(status_code=404, detail="Файл не найден")
    return RedirectResponse(url=url, status_code=307)
```

---

### Шаг 7 — Фронтенд: Очистка nginx (`frontend/nginx.conf`)

Удалить или закомментировать location `/uploads/`, так как файлы теперь раздаются напрямую из MinIO (или через API-редирект):

```nginx
# УДАЛЕНО — uploads раздаются напрямую из MinIO
# location ^~ /uploads/ {
#     proxy_pass http://promelectron-api:8000/uploads/;
# }
```

---

### Шаг 8 — Docker Compose (локальная разработка)

Добавить в `backend/docker-compose.yml`:

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

И добавить в переменные окружения сервиса `api`:

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

### Шаг 9 — Обновление тестов

Обновить `backend/tests/conftest.py`:

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

Удалить или обновить старый фикстуру `temp_upload_dirs`, так как `upload()` теперь полностью мокается.

---

### Шаг 10 — Обновление `.env.example`

Добавить в `backend/.env.example`:

```env
# --- MinIO (S3-совместимое хранилище) ---
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=promelectron-uploads
MINIO_SECURE=false

# --- Базовый URL API ---
API_BASE_URL=http://localhost:8000

# --- Окружение ---
ENVIRONMENT=development

# --- Redis ---
REDIS_URL=redis://redis:6379/0
```

---

## 5. План отката

Если что-то пойдёт не так:

1. Удалить `MINIO_ENDPOINT` в K8s → бэкенд автоматически переключится на `LocalStorageService`
2. Восстановить location `/uploads/` в `frontend/nginx.conf`
3. Включить обратно монтирование `StaticFiles` в `main.py`
4. Файлы, загруженные в период работы MinIO, будут иметь внешние URL — они станут 404, но новые загрузки снова пойдут в локальную ФС (приемлемо для тестового окружения)

---

## 6. Чек-лист проверки после деплоя

- [ ] `kubectl get pods` — под MinIO в статусе Running
- [ ] `mc ls local/promelectron-uploads` — бакет существует
- [ ] Загрузить аватар через фронтенд → `avatar_url` в БД начинается с `https://minio...`
- [ ] `curl -I <avatar_url>` → возвращает `200 OK` напрямую из MinIO
- [ ] `pytest backend/tests/` → 87 тестов пройдено
- [ ] E2E-тесты → 92 пройдено

---

## 7. Сводка изменений по файлам

| Файл | Действие | Владелец |
|------|----------|----------|
| Helm values / ConfigMap (`values-*.yaml`) | Добавить переменные окружения + creds MinIO | Evgeniy (по данным от Александра) |
| K8s secrets | Перевести creds MinIO из ConfigMap в Secret | После запуска |
| Под MinIO | Создать бакет + политику | Александр |
| `backend/requirements.txt` | Добавить `aiobotocore` | Бэкенд-разработчик |
| `backend/src/app/core/config.py` | Добавить настройки MinIO | Бэкенд-разработчик |
| `backend/src/app/services/storage_service.py` | **Новый файл** — абстракция хранилища | Бэкенд-разработчик |
| `backend/src/app/api/users.py` | Использовать `storage.upload()` | Бэкенд-разработчик |
| `backend/src/app/api/products.py` | Использовать `storage.upload()` | Бэкенд-разработчик |
| `backend/src/app/main.py` | Заменить StaticFiles на редирект | Бэкенд-разработчик |
| `frontend/nginx.conf` | Удалить proxy `/uploads/` | Фронтенд-разработчик |
| `backend/docker-compose.yml` | Добавить сервис MinIO | Александр |
| `backend/tests/conftest.py` | Замокать storage service | Бэкенд-разработчик |
| `backend/.env.example` | Добавить все недостающие переменные | Бэкенд-разработчик |
