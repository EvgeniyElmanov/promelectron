import ipaddress
import os
from dataclasses import dataclass
from urllib.parse import urlparse

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
    smtp_from_name: str
    smtp_use_tls: bool
    smtp_starttls: bool
    email_verify_token_ttl_minutes: int
    verify_base_url: str
    redis_url: str
    api_base_url: str
    storage_backend: str
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
    cdek_sync_cron_interval_seconds: int
    cdek_terminal_statuses: frozenset[str]
    job_worker_sleep_seconds: int
    job_max_attempts: int


def _parse_int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _parse_csv_env(name: str, default: str) -> frozenset[str]:
    value = os.getenv(name, default)
    return frozenset(item.strip() for item in value.split(",") if item.strip())


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


def _validate_frontend_url(url: str) -> str:
    """Validate frontend_url in production (F-09).

    Fails fast when the URL is insecure (non-https) or points at a loopback,
    private, link-local, or unspecified address — mirroring the fail-fast
    pattern of ``_load_secret_key``.  Dev/test are unaffected.
    """
    if os.getenv("ENVIRONMENT") == "production":
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise RuntimeError(
                f"FRONTEND_URL must use https:// in production. Got: {url!r}"
            )
        host = parsed.hostname or ""
        # Named loopback aliases
        if host in ("localhost",):
            raise RuntimeError(
                f"FRONTEND_URL must not point at localhost in production. Got: {url!r}"
            )
        # IP literal check — covers 127.x.x.x, ::1, 10.x, 192.168.x, 169.254.x, etc.
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified:
                raise RuntimeError(
                    f"FRONTEND_URL must not point at a loopback/private/link-local IP in "
                    f"production. Got: {url!r}"
                )
        except ValueError:
            # Not an IP literal — a real domain name, which is fine.
            pass
    return url


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
    frontend_url=_validate_frontend_url(os.getenv("FRONTEND_URL", "http://localhost:5173")),
    smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")),
    smtp_user=os.getenv("SMTP_USER", ""),
    smtp_password=os.getenv("SMTP_PASSWORD", ""),
    smtp_from=os.getenv("SMTP_FROM", "noreply@myshop.ru"),
    smtp_from_name=os.getenv("SMTP_FROM_NAME", "MyShop"),
    smtp_use_tls=os.getenv("SMTP_USE_TLS", "false").lower() == "true",
    smtp_starttls=os.getenv("SMTP_STARTTLS", os.getenv("SMTP_TLS", "true")).lower()
    == "true",
    email_verify_token_ttl_minutes=int(
        os.getenv("EMAIL_VERIFY_TOKEN_TTL_MINUTES", "60")
    ),
    verify_base_url=_validate_frontend_url(
        os.getenv("VERIFY_BASE_URL", os.getenv("FRONTEND_URL", "http://localhost:5173"))
    ),
    redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    api_base_url=os.getenv("API_BASE_URL", ""),
    storage_backend=os.getenv("STORAGE_BACKEND", "").lower(),
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
    cdek_sync_cron_interval_seconds=_parse_int_env("CDEK_SYNC_CRON_INTERVAL_SECONDS", 900),
    cdek_terminal_statuses=_parse_csv_env(
        "CDEK_TERMINAL_STATUSES", "DELIVERED,NOT_DELIVERED,RETURNED,CANCELLED"
    ),
    job_worker_sleep_seconds=_parse_int_env("JOB_WORKER_SLEEP_SECONDS", 60),
    job_max_attempts=_parse_int_env("JOB_MAX_ATTEMPTS", 5),
)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
