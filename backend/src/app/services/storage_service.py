import os
import shutil
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
            shutil.copyfileobj(file.file, buffer)
        return f"/uploads/{key}"

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

    async def upload(self, key: str, file: UploadFile) -> str:
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
                Body=await file.read(),
                ContentType=file.content_type or "application/octet-stream",
            )
        return self.get_url(key)

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


def get_storage_service() -> StorageService:
    if settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key:
        return MinioStorageService()
    return LocalStorageService()


storage = get_storage_service()
