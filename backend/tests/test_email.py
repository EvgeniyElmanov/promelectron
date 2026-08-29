from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.app.core.config import Settings, settings as original_settings
from src.app.models.job import Job
from src.app.services.email_service import EmailService


def _make_settings(**overrides) -> Settings:
    from tests.conftest import make_settings

    return make_settings(**overrides)


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

    @pytest.mark.asyncio
    async def test_send_order_paid_creates_job(self, test_session):
        """send_order_paid создаёт SEND_EMAIL job с шаблоном «Заказ оплачен»."""
        await EmailService.send_order_paid(
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
        assert "Заказ №42 оплачен" in job.payload["subject"]
        assert "оплачен" in job.payload["html"].lower()
        assert "Товар" in job.payload["html"]

    @pytest.mark.asyncio
    async def test_send_order_status_update_with_tracking(self, test_session):
        """send_order_status_update включает трек-номер и ссылку, когда они переданы."""
        tracking_url = "https://www.cdek.ru/ru/tracking?order_id=1234567890"
        await EmailService.send_order_status_update(
            to="user@example.com",
            order_id=42,
            status="shipped",
            db=test_session,
            tracking_number="1234567890",
            tracking_url=tracking_url,
        )

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEND_EMAIL")
        )
        job = result.scalars().first()
        assert job is not None
        assert "1234567890" in job.payload["html"]
        assert tracking_url in job.payload["html"]
        assert "1234567890" in job.payload["text"]

    @pytest.mark.asyncio
    async def test_send_order_status_update_without_tracking(self, test_session):
        """Без трек-номера блок отслеживания в письме не отображается."""
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
        assert "Трек-номер" not in job.payload["html"]
        assert "Трек-номер" not in job.payload["text"]
