"""Конфигурация OData мок-сервера 1С через переменные окружения."""

import os
import re
from dataclasses import dataclass

# DDL-идентификаторы нельзя биндить параметрами — валидируем имя схемы
_SCHEMA_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass
class Settings:
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron"
    # Дефолты только для локальной разработки; в compose/K8s приходят из env/секрета
    login: str = "onec"
    password: str = "onec"
    base_path: str = "/odata/standard.odata"
    onec_mock_schema: str = "onec"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.getenv("ONEC_MOCK_DATABASE_URL") or os.getenv(
            "DATABASE_URL", cls.database_url
        )
        onec_mock_schema = os.getenv("ONEC_MOCK_SCHEMA", cls.onec_mock_schema)
        if not _SCHEMA_NAME_RE.match(onec_mock_schema):
            raise ValueError(f"invalid ONEC_MOCK_SCHEMA: {onec_mock_schema!r}")
        return cls(
            database_url=database_url,
            login=os.getenv("ONEC_MOCK_LOGIN", cls.login),
            password=os.getenv("ONEC_MOCK_PASSWORD", cls.password),
            base_path=os.getenv("ONEC_MOCK_BASE_PATH", cls.base_path).rstrip("/"),
            # logging требует верхний регистр; в K8s configmap LOG_LEVEL=info (lowercase)
            log_level=os.getenv("LOG_LEVEL", cls.log_level).upper(),
            onec_mock_schema=onec_mock_schema,
        )


settings = Settings.from_env()
