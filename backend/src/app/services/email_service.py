import asyncio
import logging
import re
from email.message import EmailMessage
from html import escape as html_escape

from aiosmtplib import (
    send,
    SMTPConnectTimeoutError,
    SMTPException,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.db.database import SessionLocal
from src.app.models.job import Job

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
    ) -> str:
        """Send an email best-effort and return an outcome string.

        Never raises: transport failures are logged and reported via the
        return value so callers (e.g. the job worker) can record the real
        outcome instead of assuming success. Possible return values:

        - ``"sent"`` — accepted by the SMTP server.
        - ``"skipped:no_credentials"`` — SMTP not configured (dev/test).
        - ``"failed:recipients_refused"`` — server rejected the recipient.
        - ``"failed:transient"`` — transient errors exhausted the retries.
        - ``"failed:smtp_error"`` — a permanent SMTP/transport error.
        """
        if to.lower().split("@")[-1] == "example.com":
            # Never send to reserved test domains (RFC 2606). Prevents
            # mailer-daemon bounces from real SMTP servers in dev/test.
            logger.info(
                "[email skip] test domain: <redacted> | Subject: %s",
                subject,
            )
            return "skipped:test_domain"

        if not settings.smtp_user or not settings.smtp_password:
            # Dev/test fallback: log the email metadata instead of sending.
            # Do NOT log text_body/html_body — they may contain secrets/tokens.
            logger.info(
                "[email fallback] To: <redacted> | Subject: %s",
                subject,
            )
            return "skipped:no_credentials"

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
                return "sent"
            except SMTPRecipientsRefused as exc:
                logger.warning(
                    "SMTP recipients refused for <redacted>: %s",
                    _redact_emails(str(exc)),
                )
                return "failed:recipients_refused"
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
                return "failed:smtp_error"

        logger.warning(
            "Failed to send email to <redacted> after retries: %s",
            _redact_emails(str(last_exc)) if last_exc else "unknown",
        )
        return "failed:transient"

    @classmethod
    async def enqueue_email(
        cls,
        to: str,
        subject: str,
        html: str,
        text: str,
        db: AsyncSession,
    ) -> Job:
        """Create a SEND_EMAIL job for asynchronous delivery."""
        job = Job(
            job_type="SEND_EMAIL",
            payload={"to": to, "subject": subject, "html": html, "text": text},
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @classmethod
    async def send_verification_email(
        cls,
        to: str,
        token: str,
        base_url: str | None = None,
        db: AsyncSession | None = None,
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

        async def _enqueue(session: AsyncSession) -> None:
            await cls.enqueue_email(
                to=to,
                subject=f"{settings.smtp_from_name} — Подтверждение email",
                html=html,
                text=text,
                db=session,
            )

        if db is not None:
            await _enqueue(db)
        else:
            async with SessionLocal() as session:
                await _enqueue(session)

    @staticmethod
    def _format_price(price: float) -> str:
        return f"{price:,.0f}".replace(",", " ")

    @staticmethod
    def _order_items_html(items: list[dict]) -> str:
        rows = ""
        for item in items:
            # Escape: product_name comes from supplier/admin-controlled DB data.
            name = html_escape(str(item.get("product_name", "Товар")))
            qty = item.get("quantity", 1)
            price = item.get("price_at_time", 0)
            rows += f"<tr><td>{name}</td><td>{qty}</td><td>{EmailService._format_price(price)} ₽</td></tr>"
        return rows

    @classmethod
    async def send_order_confirmation(
        cls, to: str, order_id: int, total_price: float, items: list[dict], shipping_address: str, db: AsyncSession
    ) -> None:
        items_html = cls._order_items_html(items)
        # Escape: shipping_address is user input from checkout.
        address_html = html_escape(shipping_address) if shipping_address else "Не указан"
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

    <p><strong>Адрес доставки:</strong> {address_html}</p>

    <p style="margin-top: 24px; color: #6c757d; font-size: 12px;">
      Если у вас есть вопросы, ответьте на это письмо.
    </p>
  </div>
</body>
</html>
"""
        text = f"Заказ №{order_id} оформлен. Итого: {cls._format_price(total_price)} ₽. Адрес: {shipping_address or 'Не указан'}."
        await cls.enqueue_email(
            to=to,
            subject=f"MyShop — Заказ №{order_id} оформлен",
            html=html,
            text=text,
            db=db,
        )

    @classmethod
    async def send_order_paid(
        cls, to: str, order_id: int, total_price: float, items: list[dict], shipping_address: str, db: AsyncSession
    ) -> None:
        items_html = cls._order_items_html(items)
        # Escape: shipping_address is user input from checkout.
        address_html = html_escape(shipping_address) if shipping_address else "Не указан"
        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #181818;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <h2 style="color: #005BFF;">MyShop — Заказ оплачен</h2>
    <p>Ваш заказ <strong>№{order_id}</strong> успешно оплачен.</p>

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

    <p><strong>Адрес доставки:</strong> {address_html}</p>

    <p style="margin-top: 24px; color: #6c757d; font-size: 12px;">
      Если у вас есть вопросы, ответьте на это письмо.
    </p>
  </div>
</body>
</html>
"""
        text = f"Заказ №{order_id} оплачен. Итого: {cls._format_price(total_price)} ₽. Адрес: {shipping_address or 'Не указан'}."
        await cls.enqueue_email(
            to=to,
            subject=f"MyShop — Заказ №{order_id} оплачен",
            html=html,
            text=text,
            db=db,
        )

    @classmethod
    async def send_order_status_update(
        cls, to: str, order_id: int, status: str, db: AsyncSession,
        tracking_number: str | None = None,
        tracking_url: str | None = None,
    ) -> None:
        status_labels = {
            "pending": "Ожидает обработки",
            "paid": "Оплачен",
            "shipped": "Отправлен",
            "delivered": "Доставлен",
            "cancelled": "Отменён",
        }
        label = status_labels.get(status, status)
        tracking_html = ""
        tracking_text = ""
        if tracking_number:
            # Данные CDEK (webhook/API) — экранируем перед вставкой в HTML (S001).
            safe_tracking_number = html_escape(tracking_number, quote=True)
            tracking_html = f"""
    <p style="margin-top: 16px;"><strong>Трек-номер:</strong> {safe_tracking_number}</p>"""
            tracking_text = f" Трек-номер: {tracking_number}."
            if tracking_url:
                safe_tracking_url = html_escape(tracking_url, quote=True)
                tracking_html += f"""
    <p><a href="{safe_tracking_url}">Отследить посылку</a></p>"""
                tracking_text += f" Отследить: {tracking_url}"
        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #181818;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <h2 style="color: #005BFF;">MyShop — Обновление статуса заказа</h2>
    <p>Статус вашего заказа <strong>№{order_id}</strong> изменён:</p>
    <p style="font-size: 20px; font-weight: bold; color: #005BFF;">{label}</p>{tracking_html}
  </div>
</body>
</html>
"""
        text = f"Статус заказа №{order_id} изменён: {label}.{tracking_text}"
        await cls.enqueue_email(
            to=to,
            subject=f"MyShop — Заказ №{order_id}: {label}",
            html=html,
            text=text,
            db=db,
        )

    @classmethod
    async def send_welcome_email(
        cls, to: str, temp_password: str, reset_token: str, frontend_url: str, db: AsyncSession
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
        await cls.enqueue_email(
            to=to,
            subject="MyShop — Аккаунт создан",
            html=html,
            text=text,
            db=db,
        )
