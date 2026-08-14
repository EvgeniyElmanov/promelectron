import io
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image

from src.app.services.storage_service import (
    LocalStorageService,
    MinioStorageService,
    get_storage_service,
)


def _make_minio_service():
    """MinioStorageService с фейковой aiobotocore-сессией (без сети)."""
    with patch("src.app.services.storage_service.settings") as mock_settings:
        mock_settings.minio_endpoint = "http://minio:9000"
        mock_settings.minio_access_key = "key"
        mock_settings.minio_secret_key = "secret"
        mock_settings.minio_bucket = "promelectron-uploads"
        mock_settings.minio_secure = False
        svc = MinioStorageService()

    client = MagicMock()
    client.head_bucket = AsyncMock()
    client.create_bucket = AsyncMock()
    client.put_object = AsyncMock()
    client.delete_object = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.create_client = MagicMock(return_value=client)
    svc.session = session
    return svc, client


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


async def test_minio_upload_returns_relative_uploads_url():
    """Upload в MinIO-режиме возвращает относительный proxy-путь /uploads/{key}."""
    svc, client = _make_minio_service()
    url = await svc._upload_bytes("products/x.jpg", b"data", "image/jpeg")
    assert url == "/uploads/products/x.jpg"
    assert not url.startswith("http")
    client.put_object.assert_awaited_once()
    kwargs = client.put_object.await_args.kwargs
    assert kwargs["Bucket"] == "promelectron-uploads"
    assert kwargs["Key"] == "products/x.jpg"


async def test_minio_upload_image_returns_relative_urls():
    """upload_image возвращает /uploads/... для original и всех size-вариантов."""
    svc, client = _make_minio_service()
    content = _png_bytes()
    from fastapi import UploadFile

    file = UploadFile(filename="x.png", file=io.BytesIO(content))
    result = await svc.upload_image("products/x.png", file, content=content)
    assert result["original"] == "/uploads/products/x.png"
    assert result["small"] == "/uploads/products/x_small.webp"
    assert result["medium"] == "/uploads/products/x_medium.webp"
    assert result["large"] == "/uploads/products/x_large.webp"
    # original + 3 варианта
    assert client.put_object.await_count == 4


async def test_minio_upload_raw_other_bucket_keeps_absolute_url():
    """upload_raw для прочих бакетов (onec-intake) сохраняет absolute URL."""
    svc, client = _make_minio_service()
    url = await svc.upload_raw("imports/file.xml", b"<xml/>", "application/xml", bucket="onec-intake")
    assert url == "http://minio:9000/onec-intake/imports/file.xml"
    kwargs = client.put_object.await_args.kwargs
    assert kwargs["Bucket"] == "onec-intake"


async def test_minio_delete_strips_relative_and_absolute_prefixes():
    """delete() стрипит и /uploads/, и absolute prefix перед delete_object."""
    svc, client = _make_minio_service()

    await svc.delete("/uploads/products/x.jpg")
    assert client.delete_object.await_args.kwargs["Key"] == "products/x.jpg"

    client.delete_object.reset_mock()
    await svc.delete("http://minio:9000/promelectron-uploads/products/y.jpg")
    assert client.delete_object.await_args.kwargs["Key"] == "products/y.jpg"


def test_get_storage_service_explicit_local():
    with patch("src.app.services.storage_service.settings") as mock_settings:
        mock_settings.storage_backend = "local"
        svc = get_storage_service()
        assert isinstance(svc, LocalStorageService)


def test_get_storage_service_explicit_minio():
    with patch("src.app.services.storage_service.settings") as mock_settings:
        mock_settings.storage_backend = "minio"
        svc = get_storage_service()
        assert isinstance(svc, MinioStorageService)


def test_get_storage_service_legacy_fallback_to_minio():
    """When STORAGE_BACKEND is not set, presence of MinIO credentials selects MinIO."""
    with patch("src.app.services.storage_service.settings") as mock_settings:
        mock_settings.storage_backend = ""
        mock_settings.minio_endpoint = "http://minio:9000"
        mock_settings.minio_access_key = "key"
        mock_settings.minio_secret_key = "secret"
        svc = get_storage_service()
        assert isinstance(svc, MinioStorageService)


def test_get_storage_service_legacy_fallback_to_local():
    """When STORAGE_BACKEND is not set and MinIO credentials are absent, use local."""
    with patch("src.app.services.storage_service.settings") as mock_settings:
        mock_settings.storage_backend = ""
        mock_settings.minio_endpoint = None
        mock_settings.minio_access_key = None
        mock_settings.minio_secret_key = None
        svc = get_storage_service()
        assert isinstance(svc, LocalStorageService)
