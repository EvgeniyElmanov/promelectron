from dataclasses import replace as dataclass_replace
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.app.api.seed import SEED_SECRET
from src.app.core.config import settings
from src.app.models.order import Order
from src.app.models.payment import Payment
from src.app.schemas.order import GuestOrderCreate, GuestOrderItemCreate
from src.app.services.order_service import OrderService
from src.app.services.payment_service import PaymentService


def _guest_order_data(test_product, cdek_delivery_payload, email):
    return GuestOrderCreate(
        items=[GuestOrderItemCreate(product_id=test_product.id, quantity=1)],
        cdek_delivery=cdek_delivery_payload,
        guest_email=email,
        recipient_phone="+79990001122",
        recipient_first_name="Иван",
        recipient_last_name="Гость",
    )


async def _create_guest_order_and_payment(
    test_session, test_product, cdek_delivery_payload, guest_email, yookassa_payment_id
):
    order = await OrderService.create_guest_order(
        order_data=_guest_order_data(test_product, cdek_delivery_payload, guest_email),
        db=test_session,
    )
    mock_yookassa = AsyncMock(
        return_value={
            "yookassa_payment_id": yookassa_payment_id,
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": order.total_price,
            "created_at": "2026-06-02T12:00:00.000Z",
        }
    )
    with (
        patch(
            "src.app.services.payment_service.YooKassaService.is_configured",
            return_value=True,
        ),
        patch(
            "src.app.services.payment_service.YooKassaService.create_payment",
            mock_yookassa,
        ),
    ):
        await PaymentService.create_guest_payment(
            order_id=order.id, guest_email=guest_email, db=test_session
        )
    return order


class TestPaymentsAPI:
    """Тесты платёжного шлюза (ЮKassa)."""

    @pytest.mark.asyncio
    async def test_create_payment(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Создание платежа для заказа через ЮKassa."""
        # Сначала создаём корзину и заказ
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_id = order_resp.json()["id"]

        # Мокаем YooKassaService.create_payment
        expected_amount = Decimal(str(test_product.price)) + Decimal(
            str(cdek_delivery_payload["price"])
        )
        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": expected_amount,
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            payment_resp = await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert payment_resp.status_code == 200
        data = payment_resp.json()
        assert data["status"] == "pending"
        assert float(data["amount"]) == float(expected_amount)
        assert "payment_id" in data
        assert data["confirmation_url"] == "https://yoomoney.ru/checkout/test"

    @pytest.mark.asyncio
    async def test_create_payment_for_nonexistent_order(
        self, client, test_user, user_token
    ):
        """Платёж для несуществующего заказа — 404."""
        response = await client.post(
            "/api/v1/payments/99999/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_payment_duplicate(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Повторное создание платежа для того же заказа — возвращаем существующий."""
        # Создаём заказ
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        # Создаём платёж
        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            first = await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            assert first.status_code == 200
            first_data = first.json()

            # Повторный запрос — возвращаем тот же платёж (не 400)
            second = await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            assert second.status_code == 200
            second_data = second.json()
            assert second_data["payment_id"] == first_data["payment_id"]
            assert second_data["confirmation_url"] == first_data["confirmation_url"]

    @pytest.mark.asyncio
    async def test_get_payment(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Получение информации о платеже."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            payment_resp = await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            payment_id = payment_resp.json()["payment_id"]

        get_resp = await client.get(
            f"/api/v1/payments/{payment_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_cancel_payment(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Отмена неоплаченного платежа."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            payment_resp = await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            payment_id = payment_resp.json()["payment_id"]

        with patch(
            "src.app.services.payment_service.YooKassaService.cancel_payment",
            AsyncMock(),
        ):
            cancel_resp = await client.post(
                f"/api/v1/payments/{payment_id}/cancel/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_webhook_payment_succeeded(
        self,
        client,
        test_user,
        user_token,
        test_product,
        test_session,
        cdek_delivery_payload,
    ):
        """Webhook payment.succeeded обновляет статус заказа."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        # Отправляем webhook (raw_body передаётся автоматически через Request)
        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }

        resp = await client.post(
            "/api/v1/payments/yookassa/webhook/", json=webhook_payload
        )
        assert resp.status_code == 200

        # Проверяем статус заказа
        order_get = await client.get(
            f"/api/v1/orders/{order_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_get.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_webhook_payment_canceled_saves_cancellation_details(
        self,
        client,
        test_user,
        user_token,
        test_product,
        test_session,
        cdek_delivery_payload,
    ):
        """Webhook payment.canceled сохраняет cancellation_details в yookassa_metadata."""
        from src.app.models.payment import Payment

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        webhook_payload = {
            "event": "payment.canceled",
            "object": {
                "id": "test-yookassa-id",
                "status": "canceled",
                "cancellation_details": {
                    "party": "payment_network",
                    "reason": "fraud_suspected",
                },
            },
        }

        resp = await client.post(
            "/api/v1/payments/yookassa/webhook/", json=webhook_payload
        )
        assert resp.status_code == 200

        payment_result = await test_session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalars().first()
        assert payment.status == "cancelled"
        assert (
            payment.yookassa_metadata["cancellation_details"]["reason"]
            == "fraud_suspected"
        )

        order_get = await client.get(
            f"/api/v1/orders/{order_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_get.json()["cancellation_reason"] == "fraud_suspected"

    @pytest.mark.asyncio
    async def test_webhook_payment_canceled_invalid_csc(
        self,
        client,
        test_user,
        user_token,
        test_product,
        test_session,
        cdek_delivery_payload,
    ):
        """Webhook payment.canceled с reason=invalid_csc корректно сохраняется."""
        from src.app.models.payment import Payment

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        webhook_payload = {
            "event": "payment.canceled",
            "object": {
                "id": "test-yookassa-id",
                "status": "canceled",
                "cancellation_details": {
                    "party": "payment_network",
                    "reason": "invalid_csc",
                },
            },
        }

        resp = await client.post(
            "/api/v1/payments/yookassa/webhook/", json=webhook_payload
        )
        assert resp.status_code == 200

        payment_result = await test_session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalars().first()
        assert (
            payment.yookassa_metadata["cancellation_details"]["reason"] == "invalid_csc"
        )

        order_get = await client.get(
            f"/api/v1/orders/{order_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_get.json()["cancellation_reason"] == "invalid_csc"

    @pytest.mark.asyncio
    async def test_webhook_payment_canceled_insufficient_funds(
        self,
        client,
        test_user,
        user_token,
        test_product,
        test_session,
        cdek_delivery_payload,
    ):
        """Webhook payment.canceled с reason=insufficient_funds корректно сохраняется."""
        from src.app.models.payment import Payment

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        webhook_payload = {
            "event": "payment.canceled",
            "object": {
                "id": "test-yookassa-id",
                "status": "canceled",
                "cancellation_details": {
                    "party": "payment_network",
                    "reason": "insufficient_funds",
                },
            },
        }

        resp = await client.post(
            "/api/v1/payments/yookassa/webhook/", json=webhook_payload
        )
        assert resp.status_code == 200

        payment_result = await test_session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalars().first()
        assert (
            payment.yookassa_metadata["cancellation_details"]["reason"]
            == "insufficient_funds"
        )

    @pytest.mark.asyncio
    async def test_webhook_payment_waiting_for_capture_auto_capture(
        self,
        client,
        test_user,
        user_token,
        test_product,
        test_session,
        cdek_delivery_payload,
    ):
        """Webhook payment.waiting_for_capture автоматически делает capture и оплачивает заказ."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        webhook_payload = {
            "event": "payment.waiting_for_capture",
            "object": {
                "id": "test-yookassa-id",
                "status": "waiting_for_capture",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }

        mock_capture = AsyncMock(return_value=None)
        with (
            patch(
                "src.app.services.payment_service.YooKassaService.capture_payment",
                mock_capture,
            ),
            patch(
                "src.app.services.payment_service.EmailService.send_order_confirmation",
                AsyncMock(),
            ),
        ):
            resp = await client.post(
                "/api/v1/payments/yookassa/webhook/", json=webhook_payload
            )

        assert resp.status_code == 200
        mock_capture.assert_awaited_once_with("test-yookassa-id")

        order_get = await client.get(
            f"/api/v1/orders/{order_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_get.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_sync_payment_status_by_order_canceled_saves_cancellation_reason(
        self,
        client,
        test_user,
        user_token,
        test_product,
        test_session,
        cdek_delivery_payload,
    ):
        """Ручная синхронизация canceled-платежа сохраняет причину отказа в заказе."""
        from src.app.models.payment import Payment

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        mock_sync = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "canceled",
                "paid": False,
                "amount": Decimal(str(test_product.price)),
                "refunded_amount": Decimal("0"),
                "payment_method_type": "bank_card",
                "created_at": "2026-06-02T12:00:00.000Z",
                "captured_at": None,
                "cancellation_details": {
                    "party": "payment_network",
                    "reason": "insufficient_funds",
                },
            }
        )

        with patch(
            "src.app.services.payment_service.YooKassaService.get_payment", mock_sync
        ):
            resp = await client.post(
                f"/api/v1/payments/sync-by-order/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        payment_result = await test_session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalars().first()
        assert (
            payment.yookassa_metadata["cancellation_details"]["reason"]
            == "insufficient_funds"
        )

        order_get = await client.get(
            f"/api/v1/orders/{order_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_data = order_get.json()
        assert order_data["cancellation_reason"] == "insufficient_funds"
        assert order_data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_webhook_succeeded_idempotent(
        self,
        client,
        test_user,
        user_token,
        test_product,
        test_session,
        cdek_delivery_payload,
    ):
        """Повторная обработка payment.succeeded не приводит к дублированию side-effects."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }

        mock_notification = AsyncMock(return_value=None)
        with (
            patch(
                "src.app.services.payment_service.NotificationService.create_notification",
                mock_notification,
            ),
            patch(
                "src.app.services.payment_service.EmailService.send_order_confirmation",
                AsyncMock(),
            ),
        ):
            first = await client.post(
                "/api/v1/payments/yookassa/webhook/", json=webhook_payload
            )
            assert first.status_code == 200

            second = await client.post(
                "/api/v1/payments/yookassa/webhook/", json=webhook_payload
            )
            assert second.status_code == 200

        mock_notification.assert_awaited_once()

        order_get = await client.get(
            f"/api/v1/orders/{order_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_get.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_payment_unauthorized(self, client):
        """Без токена доступ к платежам запрещён."""
        response = await client.post("/api/v1/payments/1/")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_refund_on_cancel_paid_order(
        self,
        client,
        test_user,
        user_token,
        test_product,
        cdek_delivery_payload,
        test_session,
    ):
        """При отмене оплаченного заказа вызывается YooKassa refund и обновляется Payment."""
        from src.app.models.payment import Payment

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "test-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }
        await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)

        mock_refund = AsyncMock(
            return_value={
                "refund_id": "test-refund-id",
                "status": "succeeded",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )

        with patch(
            "src.app.services.order_service.YooKassaService.create_refund", mock_refund
        ):
            cancel_resp = await client.patch(
                f"/api/v1/orders/{order_id}/cancel/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert cancel_resp.status_code == 200
        mock_refund.assert_awaited_once()

        # Проверяем, что платёж обновился
        payment_result = await test_session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalars().first()
        assert payment.status == "refunded"
        assert float(payment.refunded_amount) == float(order_resp.json()["total_price"])


class TestPaymentDebugSetStatusAPI:
    """Тесты debug endpoint `/api/v1/payments/debug/set-status/`."""

    @pytest.mark.asyncio
    async def test_debug_set_status_succeeded(
        self,
        client,
        test_user,
        user_token,
        test_product,
        cdek_delivery_payload,
        test_session,
    ):
        """Авторизованный заказ переводится в `paid` через debug endpoint."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "debug-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )
        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={"order_id": order_id, "status": "succeeded"},
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paid"
        assert data["yookassa_status"] == "succeeded"

        order_result = await test_session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalars().first()
        assert order.status == "paid"

    @pytest.mark.asyncio
    async def test_debug_set_status_canceled(
        self,
        client,
        test_user,
        user_token,
        test_product,
        cdek_delivery_payload,
        test_session,
    ):
        """Debug endpoint сохраняет `cancellation_reason` и статус `cancelled`."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "debug-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )
        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={
                "order_id": order_id,
                "status": "canceled",
                "cancellation_reason": "insufficient_funds",
            },
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["yookassa_status"] == "canceled"

        payment_result = await test_session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = payment_result.scalars().first()
        assert (
            payment.yookassa_metadata["cancellation_details"]["reason"]
            == "insufficient_funds"
        )

        order_result = await test_session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalars().first()
        assert order.cancellation_reason == "insufficient_funds"
        assert order.status == "pending"

    @pytest.mark.asyncio
    async def test_debug_set_status_guest(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Гостевой заказ переводится в `paid` по `guest_email`."""
        guest_email = "debugguest@example.com"
        order = await _create_guest_order_and_payment(
            test_session,
            test_product,
            cdek_delivery_payload,
            guest_email,
            yookassa_payment_id="guest-debug-yookassa-id",
        )

        resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={
                "order_id": order.id,
                "status": "succeeded",
                "guest_email": guest_email,
            },
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paid"
        assert data["yookassa_status"] == "succeeded"

        order_result = await test_session.execute(
            select(Order).where(Order.id == order.id)
        )
        order = order_result.scalars().first()
        assert order.status == "paid"
        assert order.user_id is not None
        assert order.guest_email == guest_email

    @pytest.mark.asyncio
    async def test_debug_set_status_guest_missing_email(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Отсутствие `guest_email` для гостевого заказа возвращает 400."""
        guest_email = "debugguest-missing@example.com"
        order = await _create_guest_order_and_payment(
            test_session,
            test_product,
            cdek_delivery_payload,
            guest_email,
            yookassa_payment_id="guest-debug-yookassa-id",
        )

        resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={"order_id": order.id, "status": "succeeded"},
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert resp.status_code == 400
        assert "guest_email" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_debug_set_status_guest_wrong_email(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Неверный `guest_email` для гостевого заказа возвращает 404."""
        guest_email = "debugguest-wrong@example.com"
        order = await _create_guest_order_and_payment(
            test_session,
            test_product,
            cdek_delivery_payload,
            guest_email,
            yookassa_payment_id="guest-debug-yookassa-id",
        )

        resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={
                "order_id": order.id,
                "status": "succeeded",
                "guest_email": "wrong@example.com",
            },
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_debug_set_status_guest_order_with_user(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Передача `guest_email` для авторизованного заказа возвращает 400."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "debug-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )
        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={
                "order_id": order_id,
                "status": "succeeded",
                "guest_email": "user@example.com",
            },
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert resp.status_code == 400
        assert "guest order" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_debug_set_status_forbidden_without_secret(self, client):
        """Debug endpoint возвращает 403 без `x-seed-secret`."""
        resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={"order_id": 1, "status": "succeeded"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_debug_set_status_forbidden_in_prod_mode(self, client):
        """Debug endpoint возвращает 403 при `YOOKASSA_TEST_MODE=false`."""
        prod_settings = dataclass_replace(settings, yookassa_test_mode=False)
        with patch("src.app.api.payments.settings", prod_settings):
            resp = await client.post(
                "/api/v1/payments/debug/set-status/",
                json={"order_id": 1, "status": "succeeded"},
                headers={"x-seed-secret": SEED_SECRET},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_debug_set_status_already_paid(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Повторный вызов succeeded для уже оплаченного платежа возвращает 400."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "debug-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )
        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        first = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={"order_id": order_id, "status": "succeeded"},
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert first.status_code == 200
        assert first.json()["status"] == "paid"

        second = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={"order_id": order_id, "status": "succeeded"},
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert second.status_code == 400
        assert "terminal status" in second.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_debug_set_status_cancelled_then_succeeded(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """После canceled вызов succeeded для того же платежа возвращает 400."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(
            return_value={
                "yookassa_payment_id": "debug-yookassa-id",
                "status": "pending",
                "confirmation_url": "https://yoomoney.ru/checkout/test",
                "amount": Decimal(str(test_product.price)),
                "created_at": "2026-06-02T12:00:00.000Z",
            }
        )
        with (
            patch(
                "src.app.services.payment_service.YooKassaService.is_configured",
                return_value=True,
            ),
            patch(
                "src.app.services.payment_service.YooKassaService.create_payment",
                mock_yookassa,
            ),
        ):
            await client.post(
                f"/api/v1/payments/{order_id}/",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        cancel_resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={
                "order_id": order_id,
                "status": "canceled",
                "cancellation_reason": "insufficient_funds",
            },
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        succeed_resp = await client.post(
            "/api/v1/payments/debug/set-status/",
            json={"order_id": order_id, "status": "succeeded"},
            headers={"x-seed-secret": SEED_SECRET},
        )
        assert succeed_resp.status_code == 400
        assert "terminal status" in succeed_resp.json()["detail"].lower()
