"""Тесты роута GET /uploads/{path} (serve_upload в main.py).

MinIO-режим: объект стримится из MinIO через API (внутренний endpoint
недоступен браузеру, 307 redirect не работает). Local mode: FileResponse.
"""

from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient

from src.app.main import app
from src.app.services.storage_service import MinioStorageService


def _make_minio_storage(download_side_effect=None, download_return=b"image-bytes"):
    """Инстанс MinioStorageService с замоканным download_raw (isinstance-чек в main.py)."""
    with patch("src.app.services.storage_service.settings") as mock_settings:
        mock_settings.minio_endpoint = "http://minio:9000"
        mock_settings.minio_access_key = "key"
        mock_settings.minio_secret_key = "secret"
        mock_settings.minio_bucket = "promelectron-uploads"
        mock_settings.minio_secure = False
        svc = MinioStorageService()
    svc.download_raw = AsyncMock(side_effect=download_side_effect, return_value=download_return)
    return svc


async def _get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(path)


async def test_serve_upload_minio_streams_content(monkeypatch):
    """MinIO-режим: GET /uploads/{path} отдаёт контент объекта с правильным Content-Type."""
    svc = _make_minio_storage()
    monkeypatch.setattr("src.app.main.storage", svc)

    response = await _get("/uploads/products/x.jpg")

    assert response.status_code == 200
    assert response.content == b"image-bytes"
    assert response.headers["content-type"].startswith("image/jpeg")
    svc.download_raw.assert_awaited_once_with("products/x.jpg")


async def test_serve_upload_minio_size_param(monkeypatch):
    """?size=small подменяет ключ на {base}_small.webp и отдаёт image/webp."""
    svc = _make_minio_storage(download_return=b"webp-bytes")
    monkeypatch.setattr("src.app.main.storage", svc)

    response = await _get("/uploads/products/x.jpg?size=small")

    assert response.status_code == 200
    assert response.content == b"webp-bytes"
    assert response.headers["content-type"].startswith("image/webp")
    svc.download_raw.assert_awaited_once_with("products/x_small.webp")


async def test_serve_upload_invalid_size_returns_400(monkeypatch):
    svc = _make_minio_storage()
    monkeypatch.setattr("src.app.main.storage", svc)

    response = await _get("/uploads/products/x.jpg?size=bogus")

    assert response.status_code == 400
    svc.download_raw.assert_not_awaited()


async def test_serve_upload_minio_404(monkeypatch):
    """FileNotFoundError из storage превращается в 404."""
    svc = _make_minio_storage(download_side_effect=FileNotFoundError("not found"))
    monkeypatch.setattr("src.app.main.storage", svc)

    response = await _get("/uploads/products/missing.jpg")

    assert response.status_code == 404


async def test_serve_upload_local_mode_unchanged(monkeypatch, tmp_path):
    """Local mode: файл отдаётся с файловой системы, как раньше (без redirect/stream)."""
    from src.app.services.storage_service import LocalStorageService

    monkeypatch.setattr("src.app.main.storage", LocalStorageService())
    monkeypatch.chdir(tmp_path)

    filepath = tmp_path / "uploads" / "products" / "local.txt"
    filepath.parent.mkdir(parents=True)
    filepath.write_bytes(b"local-file-content")

    response = await _get("/uploads/products/local.txt")

    assert response.status_code == 200
    assert response.content == b"local-file-content"

    response = await _get("/uploads/products/absent.txt")
    assert response.status_code == 404
