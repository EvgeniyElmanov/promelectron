"""Конфигурация мок-сервера 1С через переменные окружения (D-10)."""

import os
import re
from dataclasses import dataclass

# DDL-идентификаторы нельзя биндить параметрами — валидируем имя схемы (F008)
_SCHEMA_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass
class Settings:
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron"
    onec_target_url: str = "http://api:8000/api/v1/onec/intake/"
    # Дефолт — только для локальной разработки (F007); в K8s приходит из секрета
    onec_api_key: str = "dev-onec-api-key"
    sync_interval_minutes: int = 30
    seed_on_start: bool = True
    seed_products_count: int = 200
    catalog_seed: int = 42
    log_level: str = "INFO"
    onec_mock_schema: str = "onec_mock"

    @classmethod
    def from_env(cls) -> "Settings":
        # D-03: тот же DATABASE_URL, что у backend; ONEC_MOCK_DATABASE_URL — override
        database_url = os.getenv("ONEC_MOCK_DATABASE_URL") or os.getenv(
            "DATABASE_URL", cls.database_url
        )
        onec_mock_schema = os.getenv("ONEC_MOCK_SCHEMA", cls.onec_mock_schema)
        if not _SCHEMA_NAME_RE.match(onec_mock_schema):
            raise ValueError(f"invalid ONEC_MOCK_SCHEMA: {onec_mock_schema!r}")
        return cls(
            database_url=database_url,
            onec_target_url=os.getenv("ONEC_TARGET_URL", cls.onec_target_url),
            onec_api_key=os.getenv("ONEC_API_KEY", cls.onec_api_key),
            sync_interval_minutes=int(
                os.getenv("SYNC_INTERVAL_MINUTES", cls.sync_interval_minutes)
            ),
            seed_on_start=os.getenv("SEED_ON_START", "true").lower() == "true",
            seed_products_count=int(os.getenv("SEED_PRODUCTS_COUNT", cls.seed_products_count)),
            catalog_seed=int(os.getenv("CATALOG_SEED", cls.catalog_seed)),
            # logging требует верхний регистр; в K8s configmap LOG_LEVEL=info (lowercase)
            log_level=os.getenv("LOG_LEVEL", cls.log_level).upper(),
            onec_mock_schema=onec_mock_schema,
        )


settings = Settings.from_env()
