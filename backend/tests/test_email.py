from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.app.core.config import Settings, settings as original_settings
from src.app.models.job import Job
from src.app.services.email_service import EmailService


def _make_settings(**overrides) -> Settings:
    kwargs = {
        "secret_key": original_settings.secret_key,
        "algorithm": original_settings.algorithm,
        "access_token_expire_minutes": original_settings.access_token_expire_minutes,
        "database_url": original_settings.database_url,
        "google_client_id": original_settings.google_client_id,
        "google_client_secret": original_settings.google_client_secret,
        "yandex_client_id": original_settings.yandex_client_id,
        "yandex_client_secret": original_settings.yandex_client_secret,
        "frontend_url": original_settings.frontend_url,
        "smtp_host": original_settings.smtp_host,
        "smtp_port": original_settings.smtp_port,
        "smtp_user": original_settings.smtp_user,
        "smtp_password": original_settings.smtp_password,
        "smtp_from": original_settings.smtp_from,
        "smtp_from_name": original_settings.smtp_from_name,
        "smtp_use_tls": original_settings.smtp_use_tls,
        "smtp_starttls": original_settings.smtp_starttls,
        "email_verify_token_ttl_minutes": original_settings.email_verify_token_ttl_minutes,
        "verify_base_url": original_settings.verify_base_url,
        "redis_url": original_settings.redis_url,
        "api_base_url": original_settings.api_base_url,
        "storage_backend": original_settings.storage_backend,
        "minio_endpoint": original_settings.minio_endpoint,
        "minio_access_key": original_settings.minio_access_key,
        "minio_secret_key": original_settings.minio_secret_key,
        "minio_bucket": original_settings.minio_bucket,
        "minio_secure": original_settings.minio_secure,
        "onec_api_url": original_settings.onec_api_url,
        "onec_login": original_settings.onec_login,
        "onec_password": original_settings.onec_password,
        "onec_price_type_key": original_settings.onec_price_type_key,
        "onec_warehouse_key": original_settings.onec_warehouse_key,
        "onec_webhook_api_key": original_settings.onec_webhook_api_key,
        "onec_default_supplier_id": original_settings.onec_default_supplier_id,
        "yookassa_shop_id": original_settings.yookassa_shop_id,
        "yookassa_secret_key": original_settings.yookassa_secret_key,
        "yookassa_webhook_secret": original_settings.yookassa_webhook_secret,
        "yookassa_test_mode": original_settings.yookassa_test_mode,
        "yookassa_vat_code": original_settings.yookassa_vat_code,
        "yookassa_tax_system_code": original_settings.yookassa_tax_system_code,
        "yookassa_receipt_enabled": original_settings.yookassa_receipt_enabled,
        "yookassa_capture_auto": original_settings.yookassa_capture_auto,
        "google_oauth_enabled": original_settings.google_oauth_enabled,
        "cdek_account": original_settings.cdek_account,
        "cdek_secure": original_settings.cdek_secure,
        "cdek_api_url": original_settings.cdek_api_url,
        "cdek_test_mode": original_settings.cdek_test_mode,
        "cdek_sync_cron_interval_seconds": original_settings.cdek_sync_cron_interval_seconds,
        "cdek_terminal_statuses": original_settings.cdek_terminal_statuses,
        "job_worker_sleep_seconds": original_settings.job_worker_sleep_seconds,
        "job_max_attempts": original_settings.job_max_attempts,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


class TestEmailService:
    """Тесты EmailService."""

    @pytest.mark.asyncio
    async def test_send_email_logs_when_credentials_missing(self, monkeypatch, caplog):
        """При пустых SMTP_USER/SMTP_PASSWORD письмо логируется, не падает."""
        new_settings = _make_settings(smtp_user="", smtp_password="")
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        with caplog.at_level("INFO"):
            result = await EmailService.send_email(
                to="user@realmail.test",
                subject="Test",
                html_body="<p>Hi</p>",
                text_body="secret-token-body",
            )

        assert result == "skipped:no_credentials"
        assert "email fallback" in caplog.text
        assert "To: <redacted>" in caplog.text
        assert "user@realmail.test" not in caplog.text
        # S-001: message body (which may contain secrets) must not be logged.
        assert "secret-token-body" not in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_skips_example_com(self, monkeypatch, caplog):
        """Адреса на example.com не отправляются реальным SMTP-сервером."""
        new_settings = _make_settings(smtp_user="real", smtp_password="real")
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        with caplog.at_level("INFO"):
            result = await EmailService.send_email(
                to="test_1782826586794_w3@example.com",
                subject="Test",
                html_body="<p>Hi</p>",
            )

        assert result == "skipped:test_domain"
        assert "email skip" in caplog.text
        assert "test_1782826586794_w3@example.com" not in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_returns_sent_on_success(self, monkeypatch):
        """Успешная отправка возвращает 'sent'."""
        new_settings = _make_settings(smtp_user="u", smtp_password="p")
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        with patch("src.app.services.email_service.send", new=AsyncMock()):
            result = await EmailService.send_email(
                to="user@realmail.test", subject="Test", html_body="<p>Hi</p>"
            )

        assert result == "sent"

    @pytest.mark.asyncio
    async def test_send_email_returns_failed_on_smtp_error(self, monkeypatch):
        """Постоянная SMTP-ошибка возвращает 'failed:smtp_error', не падает."""
        from aiosmtplib import SMTPException

        new_settings = _make_settings(smtp_user="u", smtp_password="p")
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        failing = AsyncMock(side_effect=SMTPException("smtp down"))
        with patch("src.app.services.email_service.send", new=failing):
            result = await EmailService.send_email(
                to="user@realmail.test", subject="Test", html_body="<p>Hi</p>"
            )

        assert result == "failed:smtp_error"

    @pytest.mark.asyncio
    async def test_send_email_uses_implicit_tls(self, monkeypatch):
        """SMTP_USE_TLS=True передаёт use_tls=True в aiosmtplib.send."""
        new_settings = _make_settings(
            smtp_user="u", smtp_password="p", smtp_use_tls=True, smtp_starttls=False
        )
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        with patch("src.app.services.email_service.send", new=AsyncMock()) as mock_send:
            await EmailService.send_email(
                to="user@realmail.test", subject="Test", html_body="<p>Hi</p>"
            )

        assert mock_send.called
        _, kwargs = mock_send.call_args
        assert kwargs.get("use_tls") is True
        assert "start_tls" not in kwargs or kwargs.get("start_tls") is None

    @pytest.mark.asyncio
    async def test_send_email_uses_starttls(self, monkeypatch):
        """SMTP_STARTTLS=True передаёт start_tls=True в aiosmtplib.send."""
        new_settings = _make_settings(
            smtp_user="u", smtp_password="p", smtp_use_tls=False, smtp_starttls=True
        )
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        with patch("src.app.services.email_service.send", new=AsyncMock()) as mock_send:
            await EmailService.send_email(
                to="user@realmail.test", subject="Test", html_body="<p>Hi</p>"
            )

        assert mock_send.called
        _, kwargs = mock_send.call_args
        assert kwargs.get("start_tls") is True
        assert "use_tls" not in kwargs or kwargs.get("use_tls") is None

    @pytest.mark.asyncio
    async def test_send_email_sets_from_header(self, monkeypatch):
        """Заголовок From содержит имя и email отправителя."""
        new_settings = _make_settings(
            smtp_user="u",
            smtp_password="p",
            smtp_from="dadeko.aleksandr@yandex.ru",
            smtp_from_name="MyShop",
        )
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        with patch("src.app.services.email_service.send", new=AsyncMock()) as mock_send:
            await EmailService.send_email(
                to="user@realmail.test", subject="Test", html_body="<p>Hi</p>"
            )

        assert mock_send.called
        call_args = mock_send.call_args
        message = call_args[0][0]
        assert message["From"] == "MyShop <dadeko.aleksandr@yandex.ru>"

    @pytest.mark.asyncio
    async def test_send_email_retries_transient_errors(self, monkeypatch):
        """Transient SMTP-ошибки retry'ятся."""
        from aiosmtplib import SMTPConnectTimeoutError, SMTPException

        new_settings = _make_settings(smtp_user="u", smtp_password="p")
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        side_effects = [
            SMTPConnectTimeoutError("timeout"),
            SMTPException("other"),
        ]

        with patch(
            "src.app.services.email_service.send", new=AsyncMock(side_effect=side_effects)
        ) as mock_send:
            await EmailService.send_email(
                to="user@realmail.test", subject="Test", html_body="<p>Hi</p>"
            )

        # First transient error retried, second non-transient stops.
        assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_send_email_redacts_exception_emails(self, monkeypatch, caplog):
        """SMTP exception messages containing recipient emails are sanitized in logs."""
        from aiosmtplib import SMTPException

        new_settings = _make_settings(smtp_user="u", smtp_password="p")
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        # Exception string intentionally contains the recipient email address.
        exc_with_email = SMTPException("5.1.1 user@example.com user not found")

        with patch(
            "src.app.services.email_service.send", new=AsyncMock(side_effect=exc_with_email)
        ):
            with caplog.at_level("WARNING"):
                await EmailService.send_email(
                    to="user@realmail.test", subject="Test", html_body="<p>Hi</p>"
                )

        assert "Failed to send email to <redacted>" in caplog.text
        assert "user@example.com" not in caplog.text
        assert "user not found" in caplog.text

    @pytest.mark.asyncio
    async def test_send_verification_email_builds_correct_link(self, monkeypatch, test_session):
        """send_verification_email формирует ссылку с verify_base_url и создаёт job."""
        new_settings = _make_settings(
            smtp_user="u",
            smtp_password="p",
            verify_base_url="https://promelectron.aidrivencode.ru",
            smtp_from_name="MyShop",
            email_verify_token_ttl_minutes=60,
        )
        monkeypatch.setattr(
            "src.app.services.email_service.settings", new_settings
        )

        async def fake_send(message, **kwargs):
            pass

        with patch("src.app.services.email_service.send", new=fake_send):
            await EmailService.send_verification_email(
                to="user@example.com", token="secret-token", db=test_session
            )

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEND_EMAIL")
        )
        job = result.scalars().first()
        assert job is not None
        assert job.payload["to"] == "user@example.com"
        assert "https://promelectron.aidrivencode.ru/verify-email?token=secret-token" in job.payload["html"]
        assert "60 минут" in job.payload["html"]

    @pytest.mark.asyncio
    async def test_enqueue_email_creates_send_email_job(self, test_session):
        """enqueue_email создаёт Job с типом SEND_EMAIL и корректным payload."""
        job = await EmailService.enqueue_email(
            to="user@example.com",
            subject="Test subject",
            html="<p>HTML</p>",
            text="Text",
            db=test_session,
        )

        assert job.id is not None
        assert job.job_type == "SEND_EMAIL"
        assert job.status == "pending"
        assert job.payload == {
            "to": "user@example.com",
            "subject": "Test subject",
            "html": "<p>HTML</p>",
            "text": "Text",
        }

        result = await test_session.execute(select(Job).where(Job.id == job.id))
        stored = result.scalars().first()
        assert stored is not None
        assert stored.payload["to"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_send_order_confirmation_creates_job(self, test_session):
        """send_order_confirmation не отправляет письмо сразу, а создаёт job."""
        await EmailService.send_order_confirmation(
            to="user@example.com",
            order_id=42,
            total_price=1500.0,
            items=[{"product_name": "Товар", "quantity": 1, "price_at_time": 1500.0}],
            shipping_address="Москва",
            db=test_session,
        )

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEND_EMAIL")
        )
        job = result.scalars().first()
        assert job is not None
        assert job.payload["to"] == "user@example.com"
        assert "Заказ №42 оформлен" in job.payload["subject"]
        assert "Товар" in job.payload["html"]

    @pytest.mark.asyncio
    async def test_send_order_status_update_creates_job(self, test_session):
        """send_order_status_update создаёт SEND_EMAIL job."""
        await EmailService.send_order_status_update(
            to="user@example.com",
            order_id=42,
            status="shipped",
            db=test_session,
        )

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEND_EMAIL")
        )
        job = result.scalars().first()
        assert job is not None
        assert job.payload["to"] == "user@example.com"
        assert "Отправлен" in job.payload["subject"]
        assert "shipped" not in job.payload["html"].lower()

    @pytest.mark.asyncio
    async def test_send_welcome_email_creates_job(self, test_session):
        """send_welcome_email создаёт SEND_EMAIL job."""
        await EmailService.send_welcome_email(
            to="user@example.com",
            temp_password="tmp123",
            reset_token="abc-token",
            frontend_url="http://localhost:5173",
            db=test_session,
        )

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEND_EMAIL")
        )
        job = result.scalars().first()
        assert job is not None
        assert job.payload["to"] == "user@example.com"
        assert "tmp123" in job.payload["html"]
        assert "abc-token" in job.payload["html"]
        assert "Сменить пароль" in job.payload["html"]
