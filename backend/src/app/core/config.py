import os
from dataclasses import dataclass


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


settings = Settings(
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"),
    algorithm=os.getenv("ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
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
    yookassa_receipt_enabled=os.getenv("YOOKASSA_RECEIPT_ENABLED", "false").lower() == "true",
)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
