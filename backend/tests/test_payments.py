from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select


class TestPaymentsAPI:
    """Тесты платёжного шлюза (ЮKassa)."""

    @pytest.mark.asyncio
    async def test_create_payment(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Создание платежа для заказа через ЮKassa."""
        # Сначала создаём корзину и заказ
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
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
        expected_amount = Decimal(str(test_product.price)) + Decimal(str(cdek_delivery_payload["price"]))
        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": expected_amount,
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
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
    async def test_create_payment_for_nonexistent_order(self, client, test_user, user_token):
        """Платёж для несуществующего заказа — 404."""
        response = await client.post(
            "/api/v1/payments/99999/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_payment_duplicate(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Повторное создание платежа для того же заказа — возвращаем существующий."""
        # Создаём заказ
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
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

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        # Создаём платёж
        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            first = await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})
            assert first.status_code == 200
            first_data = first.json()

            # Повторный запрос — возвращаем тот же платёж (не 400)
            second = await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})
            assert second.status_code == 200
            second_data = second.json()
            assert second_data["payment_id"] == first_data["payment_id"]
            assert second_data["confirmation_url"] == first_data["confirmation_url"]

    @pytest.mark.asyncio
    async def test_get_payment(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Получение информации о платеже."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
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

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            payment_resp = await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})
            payment_id = payment_resp.json()["payment_id"]

        get_resp = await client.get(f"/api/v1/payments/{payment_id}/", headers={"Authorization": f"Bearer {user_token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_cancel_payment(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Отмена неоплаченного платежа."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
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

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            payment_resp = await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})
            payment_id = payment_resp.json()["payment_id"]

        with patch("src.app.services.payment_service.YooKassaService.cancel_payment", AsyncMock()):
            cancel_resp = await client.post(f"/api/v1/payments/{payment_id}/cancel/", headers={"Authorization": f"Bearer {user_token}"})

        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_webhook_payment_succeeded(self, client, test_user, user_token, test_product, test_session, cdek_delivery_payload):
        """Webhook payment.succeeded обновляет статус заказа."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
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

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})

        # Отправляем webhook (raw_body передаётся автоматически через Request)
        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }

        resp = await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)
        assert resp.status_code == 200

        # Проверяем статус заказа
        order_get = await client.get(f"/api/v1/orders/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})
        assert order_get.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_payment_unauthorized(self, client):
        """Без токена доступ к платежам запрещён."""
        response = await client.post("/api/v1/payments/1/")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_refund_on_cancel_paid_order(self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session):
        """При отмене оплаченного заказа вызывается YooKassa refund и обновляется Payment."""
        from src.app.models.payment import Payment

        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
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

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }
        await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)

        mock_refund = AsyncMock(return_value={
            "refund_id": "test-refund-id",
            "status": "succeeded",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with patch("src.app.services.order_service.YooKassaService.create_refund", mock_refund):
            cancel_resp = await client.patch(f"/api/v1/orders/{order_id}/cancel/", headers={"Authorization": f"Bearer {user_token}"})

        assert cancel_resp.status_code == 200
        mock_refund.assert_awaited_once()

        # Проверяем, что платёж обновился
        payment_result = await test_session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = payment_result.scalars().first()
        assert payment.status == "refunded"
        assert float(payment.refunded_amount) == float(order_resp.json()["total_price"])
