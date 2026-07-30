"""Тесты конфигурации мок-сервера (D-10)."""

import logging

from onec_mock.config import Settings


def test_log_level_normalized_to_upper(monkeypatch):
    """В K8s configmap LOG_LEVEL=info (lowercase) — logging требует верхний регистр."""
    monkeypatch.setenv("LOG_LEVEL", "info")
    settings = Settings.from_env()
    assert settings.log_level == "INFO"
    # Не должно падать, как в CrashLoopBackOff на test-окружении
    logging.basicConfig(level=settings.log_level)


def test_log_level_default(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert Settings.from_env().log_level == "INFO"
