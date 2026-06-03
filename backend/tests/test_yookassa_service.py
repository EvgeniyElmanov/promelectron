from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.app.services.yookassa_service import YooKassaService


class TestYooKassaService:
    """Unit tests for YooKassaService with mocked SDK."""

    @pytest.mark.asyncio
    async def test_create_payment_success(self):
        mock_response = MagicMock()
        mock_response.id = "test-payment-id"
        mock_response.status = "pending"
        mock_response.amount.value = "100.00"
        mock_response.created_at = "2026-06-02T12:00:00.000Z"
        mock_response.test = True
        mock_confirmation = MagicMock()
        mock_confirmation.confirmation_url = "https://yoomoney.ru/checkout/test"
        mock_response.confirmation = mock_confirmation

        with patch("src.app.services.yookassa_service.Payment.create", return_value=mock_response):
            result = await YooKassaService.create_payment(
                order_id=1,
                amount=Decimal("100.00"),
                description="Заказ №1",
                user_id=42,
            )

        assert result["yookassa_payment_id"] == "test-payment-id"
        assert result["status"] == "pending"
        assert result["confirmation_url"] == "https://yoomoney.ru/checkout/test"
        assert result["amount"] == Decimal("100.00")
        assert result["test"] is True

    @pytest.mark.asyncio
    async def test_get_payment_success(self):
        mock_response = MagicMock()
        mock_response.id = "test-payment-id"
        mock_response.status = "succeeded"
        mock_response.amount.value = "200.00"
        mock_response.paid = True
        mock_response.refunded_amount = None
        mock_payment_method = MagicMock()
        mock_payment_method.type = "bank_card"
        mock_response.payment_method = mock_payment_method
        mock_response.created_at = "2026-06-02T12:00:00.000Z"
        mock_response.captured_at = "2026-06-02T12:05:00.000Z"

        with patch("src.app.services.yookassa_service.Payment.find_one", return_value=mock_response):
            result = await YooKassaService.get_payment("test-payment-id")

        assert result["yookassa_payment_id"] == "test-payment-id"
        assert result["status"] == "succeeded"
        assert result["paid"] is True
        assert result["amount"] == Decimal("200.00")
        assert result["payment_method_type"] == "bank_card"

    @pytest.mark.asyncio
    async def test_cancel_payment_success(self):
        mock_response = MagicMock()
        mock_response.id = "test-payment-id"
        mock_response.status = "canceled"

        with patch("src.app.services.yookassa_service.Payment.cancel", return_value=mock_response):
            result = await YooKassaService.cancel_payment("test-payment-id")

        assert result["yookassa_payment_id"] == "test-payment-id"
        assert result["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_create_refund_success(self):
        mock_response = MagicMock()
        mock_response.id = "test-refund-id"
        mock_response.status = "succeeded"
        mock_response.amount.value = "50.00"
        mock_response.created_at = "2026-06-02T12:10:00.000Z"

        with patch("src.app.services.yookassa_service.Refund.create", return_value=mock_response):
            result = await YooKassaService.create_refund(
                yookassa_payment_id="test-payment-id",
                amount=Decimal("50.00"),
                description="Частичный возврат",
            )

        assert result["refund_id"] == "test-refund-id"
        assert result["status"] == "succeeded"
        assert result["amount"] == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_create_payment_bad_request(self):
        from yookassa.domain.exceptions.bad_request_error import BadRequestError

        with patch(
            "src.app.services.yookassa_service.Payment.create",
            side_effect=BadRequestError({"code": "invalid_amount", "description": "Invalid amount"}),
        ):
            with pytest.raises(Exception) as exc_info:
                await YooKassaService.create_payment(
                    order_id=1,
                    amount=Decimal("-10.00"),
                    description="Bad order",
                )
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_payment_not_found(self):
        from yookassa.domain.exceptions.not_found_error import NotFoundError

        with patch(
            "src.app.services.yookassa_service.Payment.find_one",
            side_effect=NotFoundError({"code": "not_found", "description": "Payment not found"}),
        ):
            with pytest.raises(Exception) as exc_info:
                await YooKassaService.get_payment("nonexistent-id")
            assert exc_info.value.status_code == 404
