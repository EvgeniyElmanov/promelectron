import io
import os
import shutil
from typing import Protocol

from aiobotocore.session import get_session
from fastapi import UploadFile
from PIL import Image

from src.app.core.config import settings


class StorageService(Protocol):
    async def upload(self, key: str, file: UploadFile) -> str:
        ...

    async def upload_image(self, key: str, file: UploadFile) -> dict:
        ...

    def get_url(self, key: str) -> str:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def delete_image(self, key: str) -> None:
        ...


class LocalStorageService:
    """Fallback для локальной разработки без MinIO."""

    def _upload_bytes(self, key: str, content: bytes, content_type: str) -> str:
        filepath = os.path.join("uploads", key)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as buffer:
            buffer.write(content)
        return f"/uploads/{key}"

    async def upload(self, key: str, file: UploadFile) -> str:
        content = await file.read()
        return self._upload_bytes(key, content, file.content_type or "application/octet-stream")

    async def upload_image(self, key: str, file: UploadFile) -> dict:
        content = await file.read()
        original_url = self._upload_bytes(
            key, content, file.content_type or "application/octet-stream"
        )

        base, _ = os.path.splitext(key)
        result = {"original": original_url}

        try:
            img = Image.open(io.BytesIO(content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            sizes = {
                "small": (300, 300),
                "medium": (800, 800),
                "large": (1600, 1600),
            }

            for size_name, (max_w, max_h) in sizes.items():
                resized = img.copy()
                resized.thumbnail((max_w, max_h))
                buf = io.BytesIO()
                resized.save(buf, format="WEBP", quality=85)
                buf.seek(0)
                variant_key = f"{base}_{size_name}.webp"
                variant_url = self._upload_bytes(variant_key, buf.getvalue(), "image/webp")
                result[size_name] = variant_url
        except Exception:
            # Если обработка изображения не удалась — возвращаем оригинал для всех размеров
            result["small"] = original_url
            result["medium"] = original_url
            result["large"] = original_url

        return result

    def get_url(self, key: str) -> str:
        return f"/uploads/{key}"

    async def delete(self, key: str) -> None:
        if key.startswith("/uploads/"):
            key = key[len("/uploads/"):]
        elif settings.api_base_url and key.startswith(f"{settings.api_base_url.rstrip('/')}/uploads/"):
            key = key[len(f"{settings.api_base_url.rstrip('/')}/uploads/"):]
        filepath = os.path.join("uploads", key)
        if os.path.exists(filepath):
            os.remove(filepath)

    async def delete_image(self, key: str) -> None:
        await self.delete(key)
        base, _ = os.path.splitext(key)
        for size in ("small", "medium", "large"):
            await self.delete(f"{base}_{size}.webp")


class MinioStorageService:
    """Продакшен-хранилище через MinIO (S3-совместимый)."""

    def __init__(self):
        self.endpoint = settings.minio_endpoint
        self.access_key = settings.minio_access_key
        self.secret_key = settings.minio_secret_key
        self.bucket = settings.minio_bucket
        self.secure = settings.minio_secure
        self.session = get_session()

    async def _ensure_bucket(self, client) -> None:
        try:
            await client.head_bucket(Bucket=self.bucket)
        except Exception:
            await client.create_bucket(Bucket=self.bucket)

    async def _upload_bytes(self, key: str, content: bytes, content_type: str) -> str:
        async with self.session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.secure,
        ) as client:
            await self._ensure_bucket(client)
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        return self.get_url(key)

    async def upload(self, key: str, file: UploadFile) -> str:
        content = await file.read()
        return await self._upload_bytes(key, content, file.content_type or "application/octet-stream")

    async def upload_image(self, key: str, file: UploadFile) -> dict:
        content = await file.read()
        original_url = await self._upload_bytes(
            key, content, file.content_type or "application/octet-stream"
        )

        base, _ = os.path.splitext(key)
        result = {"original": original_url}

        try:
            img = Image.open(io.BytesIO(content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            sizes = {
                "small": (300, 300),
                "medium": (800, 800),
                "large": (1600, 1600),
            }

            for size_name, (max_w, max_h) in sizes.items():
                resized = img.copy()
                resized.thumbnail((max_w, max_h))
                buf = io.BytesIO()
                resized.save(buf, format="WEBP", quality=85)
                buf.seek(0)
                variant_key = f"{base}_{size_name}.webp"
                variant_url = await self._upload_bytes(variant_key, buf.getvalue(), "image/webp")
                result[size_name] = variant_url
        except Exception:
            result["small"] = original_url
            result["medium"] = original_url
            result["large"] = original_url

        return result

    def get_url(self, key: str) -> str:
        scheme = "https" if self.secure else "http"
        host = self.endpoint.replace("http://", "").replace("https://", "")
        return f"{scheme}://{host}/{self.bucket}/{key}"

    async def delete(self, key: str) -> None:
        prefix = self.get_url("")
        if key.startswith(prefix):
            key = key[len(prefix):]
        elif settings.api_base_url and key.startswith(f"{settings.api_base_url.rstrip('/')}/uploads/"):
            key = key[len(f"{settings.api_base_url.rstrip('/')}/uploads/"):]
        async with self.session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.secure,
        ) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    async def delete_image(self, key: str) -> None:
        await self.delete(key)
        base, _ = os.path.splitext(key)
        for size in ("small", "medium", "large"):
            await self.delete(f"{base}_{size}.webp")


def get_storage_service() -> StorageService:
    if settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key:
        return MinioStorageService()
    return LocalStorageService()


storage = get_storage_service()
