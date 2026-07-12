from unittest.mock import patch

import pytest

from src.app.services.storage_service import (
    LocalStorageService,
    MinioStorageService,
    get_storage_service,
)


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
