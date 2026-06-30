import asyncio
import logging
import re
from email.message import EmailMessage

from aiosmtplib import (
    send,
    SMTPConnectTimeoutError,
    SMTPException,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
)

from src.app.core.config import settings

logger = logging.getLogger(__name__)

_TRANSIENT_ERRORS = (SMTPConnectTimeoutError, SMTPServerDisconnected)

# Matches typical email addresses so we can redact them from exception messages.
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")


def _redact_emails(text: str) -> str:
    """Replace any email-like substrings with <redacted>."""
    return _EMAIL_RE.sub("<redacted>", text)


class EmailService:
    @staticmethod
    async def send_email(
        to: str,
        subject: str,
        html_body: str,
        text_body: str = "",
    ) -> None:
        if not settings.smtp_user or not settings.smtp_password:
            # Dev/test fallback: log the email metadata instead of sending.
            # Do NOT log text_body/html_body — they may contain secrets/tokens.
            logger.info(
                "[email fallback] To: <redacted> | Subject: %s",
                subject,
            )
            return

        message = EmailMessage()
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text_body or "")
        message.add_alternative(html_body, subtype="html")

        last_exc: Exception | None = None
        for attempt, delay in enumerate((0.0, 0.5, 1.0)):
            try:
                if delay:
                    await asyncio.sleep(delay)

                kwargs: dict = {
                    "hostname": settings.smtp_host,
                    "port": settings.smtp_port,
                    "username": settings.smtp_user,
                    "password": settings.smtp_password,
                }
                if settings.smtp_use_tls:
                    kwargs["use_tls"] = True
                elif settings.smtp_starttls:
                    kwargs["start_tls"] = True

                await asyncio.wait_for(send(message, **kwargs), timeout=5.0)
                return
            except SMTPRecipientsRefused as exc:
                logger.warning(
                    "SMTP recipients refused for <redacted>: %s",
                    _redact_emails(str(exc)),
                )
                return
            except _TRANSIENT_ERRORS as exc:
                last_exc = exc
                logger.warning(
                    "Transient SMTP error (attempt %d) for <redacted>: %s",
                    attempt + 1,
                    _redact_emails(str(exc)),
                )
                continue
            except (SMTPException, asyncio.TimeoutError, OSError) as exc:
                logger.warning(
                    "Failed to send email to <redacted>: %s",
                    _redact_emails(str(exc)),
                )
                return

        logger.warning(
            "Failed to send email to <redacted> after retries: %s",
            _redact_emails(str(last_exc)) if last_exc else "unknown",
        )

    @classmethod
    async def send_verification_email(
        cls,
        to: str,
        token: str,
        base_url: str | None = None,
    ) -> None:
        base = (base_url or settings.verify_base_url or settings.frontend_url).rstrip("/")
        verify_url = f"{base}/verify-email?token={token}"
        ttl_minutes = settings.email_verify_token_ttl_minutes

        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #181818;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <h2 style="color: #005BFF;">{settings.smtp_from_name} — Подтверждение email</h2>
    <p>Спасибо за регистрацию! Для завершения подтверждения email перейдите по ссылке:</p>
    <p>
      <a href="{verify_url}" style="display: inline-block; padding: 12px 24px; background: #005BFF; color: #fff; text-decoration: none; border-radius: 6px;">
        Подтвердить email
      </a>
    </p>
    <p>Или скопируйте ссылку в адресную строку: <a href="{verify_url}">{verify_url}</a></p>
    <p style="color: #6c757d; font-size: 12px;">Ссылка действительна {ttl_minutes} минут.</p>
  </div>
</body>
</html>
"""
        text = (
            f"Подтверждение email. Перейдите по ссылке: {verify_url} "
            f"(действует {ttl_minutes} минут)."
        )
        await cls.send_email(
            to,
            f"{settings.smtp_from_name} — Подтверждение email",
            html,
            text,
        )

    @staticmethod
    def _format_price(price: float) -> str:
        return f"{price:,.0f}".replace(",", " ")

    @staticmethod
    def _order_items_html(items: list[dict]) -> str:
        rows = ""
        for item in items:
            name = item.get("product_name", "Товар")
            qty = item.get("quantity", 1)
            price = item.get("price_at_time", 0)
            rows += f"<tr><td>{name}</td><td>{qty}</td><td>{EmailService._format_price(price)} ₽</td></tr>"
        return rows

    @classmethod
    async def send_order_confirmation(
        cls, to: str, order_id: int, total_price: float, items: list[dict], shipping_address: str
    ) -> None:
        items_html = cls._order_items_html(items)
        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #181818;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <h2 style="color: #005BFF;">MyShop — Заказ оформлен</h2>
    <p>Спасибо за покупку! Ваш заказ <strong>№{order_id}</strong> принят.</p>

    <h3 style="margin-top: 24px;">Товары</h3>
    <table style="width: 100%; border-collapse: collapse;">
      <tr style="background: #f2f5f9;">
        <th style="padding: 8px; text-align: left;">Товар</th>
        <th style="padding: 8px; text-align: center;">Кол-во</th>
        <th style="padding: 8px; text-align: right;">Цена</th>
      </tr>
      {items_html}
    </table>

    <p style="margin-top: 16px; font-size: 18px; font-weight: bold;">
      Итого: {cls._format_price(total_price)} ₽
    </p>

    <p><strong>Адрес доставки:</strong> {shipping_address or "Не указан"}</p>

    <p style="margin-top: 24px; color: #6c757d; font-size: 12px;">
      Если у вас есть вопросы, ответьте на это письмо.
    </p>
  </div>
</body>
</html>
"""
        text = f"Заказ №{order_id} оформлен. Итого: {cls._format_price(total_price)} ₽. Адрес: {shipping_address or 'Не указан'}."
        await cls.send_email(to, f"MyShop — Заказ №{order_id} оформлен", html, text)

    @classmethod
    async def send_order_status_update(
        cls, to: str, order_id: int, status: str
    ) -> None:
        status_labels = {
            "pending": "Ожидает обработки",
            "paid": "Оплачен",
            "shipped": "Отправлен",
            "delivered": "Доставлен",
            "cancelled": "Отменён",
        }
        label = status_labels.get(status, status)
        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #181818;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <h2 style="color: #005BFF;">MyShop — Обновление статуса заказа</h2>
    <p>Статус вашего заказа <strong>№{order_id}</strong> изменён:</p>
    <p style="font-size: 20px; font-weight: bold; color: #005BFF;">{label}</p>
  </div>
</body>
</html>
"""
        text = f"Статус заказа №{order_id} изменён: {label}"
        await cls.send_email(to, f"MyShop — Заказ №{order_id}: {label}", html, text)

    @classmethod
    async def send_welcome_email(
        cls, to: str, temp_password: str, reset_token: str, frontend_url: str
    ) -> None:
        reset_url = f"{frontend_url.rstrip('/')}/reset-password?token={reset_token}"
        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #181818;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <h2 style="color: #005BFF;">MyShop — Аккаунт создан</h2>
    <p>Спасибо за покупку! Мы автоматически создали для вас личный кабинет.</p>

    <p><strong>Ваш временный пароль:</strong> {temp_password}</p>

    <p>Для безопасности рекомендуем сразу сменить пароль по ссылке ниже:</p>
    <p>
      <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background: #005BFF; color: #fff; text-decoration: none; border-radius: 6px;">
        Сменить пароль
      </a>
    </p>
    <p style="color: #6c757d; font-size: 12px;">Ссылка действительна 24 часа.</p>

    <p style="margin-top: 24px; color: #6c757d; font-size: 12px;">
      Если у вас есть вопросы, ответьте на это письмо.
    </p>
  </div>
</body>
</html>
"""
        text = (
            f"Ваш аккаунт MyShop создан. Временный пароль: {temp_password}. "
            f"Сменить пароль: {reset_url} (действует 24 часа)."
        )
        await cls.send_email(to, "MyShop — Аккаунт создан", html, text)
