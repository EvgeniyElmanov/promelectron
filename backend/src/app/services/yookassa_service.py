import asyncio
import logging
import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from yookassa import Configuration, Payment, Refund
from yookassa.domain.exceptions.api_error import ApiError
from yookassa.domain.exceptions.bad_request_error import BadRequestError
from yookassa.domain.exceptions.forbidden_error import ForbiddenError
from yookassa.domain.exceptions.not_found_error import NotFoundError
from yookassa.domain.exceptions.too_many_request_error import TooManyRequestsError
from yookassa.domain.exceptions.unauthorized_error import UnauthorizedError

from src.app.core.config import settings

logger = logging.getLogger(__name__)

# Configure YooKassa SDK once at import time
if settings.yookassa_shop_id and settings.yookassa_secret_key:
    Configuration.configure(
        account_id=settings.yookassa_shop_id,
        secret_key=settings.yookassa_secret_key,
    )
    if settings.yookassa_test_mode:
        Configuration.configure_logger(logging.getLogger("yookassa"))
else:
    logger.warning(
        "YooKassa credentials not configured. "
        "Set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY env vars."
    )


class YooKassaService:
    """Service for interacting with YooKassa API."""

    @staticmethod
    def _build_return_url(order_id: int) -> str:
        base = settings.frontend_url.rstrip("/")
        return f"{base}/payment/success?order_id={order_id}"

    @staticmethod
    def _ensure_configured() -> None:
        """Ensure YooKassa SDK is configured with valid credentials."""
        if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
            raise HTTPException(
                status_code=503,
                detail="YooKassa is not configured. Set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY.",
            )

    @staticmethod
    def _handle_sdk_error(error: ApiError) -> None:
        """Convert YooKassa SDK exceptions to HTTPException.

        Note: UnauthorizedError from YooKassa means SHOP credentials are invalid,
        NOT that the end-user is unauthorized. We return 502 to avoid triggering
        frontend auto-logout on 401.
        """
        message = getattr(error, "detail", str(error))
        if isinstance(error, BadRequestError):
            raise HTTPException(status_code=400, detail=f"YooKassa bad request: {message}")
        if isinstance(error, UnauthorizedError):
            raise HTTPException(status_code=502, detail="YooKassa shop credentials invalid")
        if isinstance(error, ForbiddenError):
            raise HTTPException(status_code=403, detail="YooKassa forbidden")
        if isinstance(error, NotFoundError):
            raise HTTPException(status_code=404, detail="YooKassa payment not found")
        if isinstance(error, TooManyRequestsError):
            raise HTTPException(status_code=429, detail="YooKassa rate limit exceeded")
        raise HTTPException(status_code=502, detail=f"YooKassa error: {message}")

    @classmethod
    async def create_payment(
        cls,
        order_id: int,
        amount: Decimal,
        description: str,
        user_id: int | None = None,
        receipt_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cls._ensure_configured()
        """Create a new payment in YooKassa.

        Returns dict with:
            - yookassa_payment_id: str
            - status: str
            - confirmation_url: str
            - amount: Decimal
            - created_at: str (ISO 8601)
        """
        idempotence_key = str(uuid.uuid4())

        params: dict[str, Any] = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": cls._build_return_url(order_id),
            },
            "description": description[:128],
            "metadata": {
                "order_id": str(order_id),
                "user_id": str(user_id) if user_id else "guest",
            },
        }

        if receipt_data:
            params["receipt"] = receipt_data

        logger.info(
            "Creating YooKassa payment for order %s, amount %s",
            order_id,
            amount,
        )

        try:
            response = await asyncio.to_thread(
                Payment.create,
                params,
                idempotency_key=idempotence_key,
            )
        except ApiError as exc:
            logger.exception("YooKassa create_payment failed")
            cls._handle_sdk_error(exc)

        result = response
        confirmation = result.confirmation or {}

        return {
            "yookassa_payment_id": result.id,
            "status": result.status,
            "confirmation_url": getattr(confirmation, "confirmation_url", None),
            "amount": Decimal(str(result.amount.value)),
            "created_at": result.created_at,
            "test": getattr(result, "test", False),
        }

    @classmethod
    async def get_payment(cls, yookassa_payment_id: str) -> dict[str, Any]:
        cls._ensure_configured()
        """Get payment info from YooKassa."""
        try:
            response = await asyncio.to_thread(
                Payment.find_one,
                yookassa_payment_id,
            )
        except ApiError as exc:
            logger.exception("YooKassa get_payment failed")
            cls._handle_sdk_error(exc)

        return {
            "yookassa_payment_id": response.id,
            "status": response.status,
            "paid": getattr(response, "paid", False),
            "amount": Decimal(str(response.amount.value)),
            "refunded_amount": Decimal(str(getattr(response, "refunded_amount", {}).get("value", "0")))
            if getattr(response, "refunded_amount", None)
            else Decimal("0"),
            "payment_method_type": getattr(
                getattr(response, "payment_method", None),
                "type",
                None,
            ),
            "created_at": response.created_at,
            "captured_at": getattr(response, "captured_at", None),
        }

    @classmethod
    async def cancel_payment(cls, yookassa_payment_id: str) -> dict[str, Any]:
        cls._ensure_configured()
        """Cancel a payment in waiting_for_capture status."""
        idempotence_key = str(uuid.uuid4())

        try:
            response = await asyncio.to_thread(
                Payment.cancel,
                yookassa_payment_id,
                idempotency_key=idempotence_key,
            )
        except ApiError as exc:
            logger.exception("YooKassa cancel_payment failed")
            cls._handle_sdk_error(exc)

        return {
            "yookassa_payment_id": response.id,
            "status": response.status,
        }

    @classmethod
    async def create_refund(
        cls,
        yookassa_payment_id: str,
        amount: Decimal,
        description: str = "Возврат",
    ) -> dict[str, Any]:
        cls._ensure_configured()
        """Create a refund for a succeeded payment."""
        idempotence_key = str(uuid.uuid4())

        params: dict[str, Any] = {
            "payment_id": yookassa_payment_id,
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB",
            },
            "description": description[:128],
        }

        try:
            response = await asyncio.to_thread(
                Refund.create,
                params,
                idempotency_key=idempotence_key,
            )
        except ApiError as exc:
            logger.exception("YooKassa create_refund failed")
            cls._handle_sdk_error(exc)

        return {
            "refund_id": response.id,
            "status": response.status,
            "amount": Decimal(str(response.amount.value)),
            "created_at": response.created_at,
        }
