import os
from dataclasses import dataclass

# Dev-only placeholder — NEVER use in production.
# In production the real value comes from the SECRET_KEY env var
# (sops-encrypted in infra/helm/stage/*/secrets.yaml, or GitHub Secret OVR_SECRET_KEY).
_DEV_SECRET_PLACEHOLDER = "dev-only-insecure-change-me"


@dataclass(frozen=True)
class Settings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    database_url: str
    google_client_id: str
    google_client_secret: str
    yandex_client_id: str
    yandex_client_secret: str
    frontend_url: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_tls: bool
    redis_url: str
    api_base_url: str
    minio_endpoint: str | None
    minio_access_key: str | None
    minio_secret_key: str | None
    minio_bucket: str
    minio_secure: bool
    onec_api_url: str | None
    onec_api_key: str | None
    yookassa_shop_id: str
    yookassa_secret_key: str
    yookassa_webhook_secret: str | None
    yookassa_test_mode: bool
    yookassa_vat_code: int
    yookassa_tax_system_code: int
    yookassa_receipt_enabled: bool
    yookassa_capture_auto: bool
    google_oauth_enabled: bool
    cdek_account: str
    cdek_secure: str
    cdek_api_url: str
    cdek_test_mode: bool


def _load_secret_key() -> str:
    """Return SECRET_KEY from env. In production, fail fast if absent or placeholder."""
    key = os.getenv("SECRET_KEY", _DEV_SECRET_PLACEHOLDER)
    if os.getenv("ENVIRONMENT") == "production":
        if not key or key == _DEV_SECRET_PLACEHOLDER:
            raise RuntimeError(
                "SECRET_KEY must be set to a strong random value in production. "
                "Set the SECRET_KEY environment variable (never use the dev placeholder)."
            )
    return key


settings = Settings(
    secret_key=_load_secret_key(),
    algorithm=os.getenv("ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")),
    database_url=os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost/shop_db"
    ),
    google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    yandex_client_id=os.getenv("YANDEX_CLIENT_ID", ""),
    yandex_client_secret=os.getenv("YANDEX_CLIENT_SECRET", ""),
    frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173"),
    smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")),
    smtp_user=os.getenv("SMTP_USER", ""),
    smtp_password=os.getenv("SMTP_PASSWORD", ""),
    smtp_from=os.getenv("SMTP_FROM", "noreply@myshop.ru"),
    smtp_tls=os.getenv("SMTP_TLS", "true").lower() == "true",
    redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    api_base_url=os.getenv("API_BASE_URL", ""),
    minio_endpoint=os.getenv("MINIO_ENDPOINT"),
    minio_access_key=os.getenv("MINIO_ACCESS_KEY"),
    minio_secret_key=os.getenv("MINIO_SECRET_KEY"),
    minio_bucket=os.getenv("MINIO_BUCKET", "promelectron-uploads"),
    minio_secure=os.getenv("MINIO_SECURE", "true").lower() == "true",
    onec_api_url=os.getenv("ONEC_API_URL"),
    onec_api_key=os.getenv("ONEC_API_KEY"),
    yookassa_shop_id=os.getenv("YOOKASSA_SHOP_ID", ""),
    yookassa_secret_key=os.getenv("YOOKASSA_SECRET_KEY", ""),
    yookassa_webhook_secret=os.getenv("YOOKASSA_WEBHOOK_SECRET"),
    yookassa_test_mode=os.getenv("YOOKASSA_TEST_MODE", "true").lower() == "true",
    yookassa_vat_code=int(os.getenv("YOOKASSA_VAT_CODE", "1")),
    yookassa_tax_system_code=int(os.getenv("YOOKASSA_TAX_SYSTEM_CODE", "1")),
    yookassa_receipt_enabled=os.getenv("YOOKASSA_RECEIPT_ENABLED", "false").lower()
    == "true",
    yookassa_capture_auto=os.getenv("YOOKASSA_CAPTURE_AUTO", "true").lower() == "true",
    google_oauth_enabled=os.getenv("GOOGLE_OAUTH_ENABLED", "true").lower() == "true",
    cdek_account=os.getenv("CDEK_ACCOUNT", ""),
    cdek_secure=os.getenv("CDEK_SECURE", ""),
    cdek_api_url=os.getenv("CDEK_API_URL", "https://api.edu.cdek.ru"),
    cdek_test_mode=os.getenv("CDEK_TEST_MODE", "true").lower() == "true",
)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
