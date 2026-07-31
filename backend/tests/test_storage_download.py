"""Тесты метода чтения StorageService.download_raw (gap Фазы 4, #120)."""

import os

import pytest

from src.app.services.storage_service import LocalStorageService, MinioStorageService


@pytest.mark.asyncio
async def test_local_download_raw_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = LocalStorageService()

    await service.upload_raw("2026/07/31/test.bin", b"payload-bytes", "application/octet-stream")
    assert await service.download_raw("2026/07/31/test.bin") == b"payload-bytes"


@pytest.mark.asyncio
async def test_local_download_raw_with_bucket(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = LocalStorageService()

    await service.upload_raw("obj.bin", b"intake", "application/octet-stream", bucket="onec-intake")
    assert await service.download_raw("obj.bin", bucket="onec-intake") == b"intake"
    # Файл реально лежит в namespaced-пути bucket/key, как и при upload_raw
    assert os.path.exists(tmp_path / "uploads" / "onec-intake" / "obj.bin")


@pytest.mark.asyncio
async def test_local_download_raw_missing_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = LocalStorageService()

    with pytest.raises(FileNotFoundError):
        await service.download_raw("no/such/object.bin")


class _FakeStream:
    def __init__(self, data: bytes):
        self._data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def read(self):
        return self._data


class _FakeS3Client:
    def __init__(self, objects: dict, exc: Exception | None = None):
        self._objects = objects
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_object(self, Bucket, Key):
        if self._exc is not None:
            raise self._exc
        return {"Body": _FakeStream(self._objects[(Bucket, Key)])}


class _FakeSession:
    def __init__(self, client):
        self._client = client

    def create_client(self, *args, **kwargs):
        return self._client


@pytest.mark.asyncio
async def test_minio_download_raw_roundtrip(monkeypatch):
    service = MinioStorageService()
    client = _FakeS3Client({(service.bucket, "k.bin"): b"minio-bytes"})
    monkeypatch.setattr(service, "session", _FakeSession(client))

    assert await service.download_raw("k.bin") == b"minio-bytes"


@pytest.mark.asyncio
async def test_minio_download_raw_missing_raises(monkeypatch):
    class _NoSuchKeyError(Exception):
        response = {"Error": {"Code": "NoSuchKey"}}

    service = MinioStorageService()
    client = _FakeS3Client({}, exc=_NoSuchKeyError("missing"))
    monkeypatch.setattr(service, "session", _FakeSession(client))

    with pytest.raises(FileNotFoundError):
        await service.download_raw("missing.bin", bucket="onec-intake")
