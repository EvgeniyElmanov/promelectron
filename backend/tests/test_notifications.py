import pytest


class TestNotificationsAPI:
    """Тесты уведомлений."""

    @pytest.mark.asyncio
    async def test_create_order_generates_notification(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Создание заказа генерирует уведомление."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        response = await client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["type"] == "order_created"
        assert "Заказ оформлен" in data["items"][0]["title"]

    @pytest.mark.asyncio
    async def test_payment_generates_notification(self, client, test_user, user_token, test_product, cdek_delivery_payload, signed_webhook):
        """Оплата генерирует уведомление."""
        from unittest.mock import AsyncMock, patch
        from decimal import Decimal

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

        # Имитируем webhook от ЮKassa
        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(order_resp.json()["total_price"]), "currency": "RUB"},
            },
        }
        await signed_webhook(client, webhook_payload)

        response = await client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        data = response.json()
        types = [n["type"] for n in data["items"]]
        assert "order_paid" in types

    @pytest.mark.asyncio
    async def test_mark_notification_as_read(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Отметка уведомления как прочитанного."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        response = await client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {user_token}"})
        notification_id = response.json()["items"][0]["id"]
        assert response.json()["items"][0]["is_read"] is False

        patch_resp = await client.patch(f"/api/v1/notifications/{notification_id}/read", headers={"Authorization": f"Bearer {user_token}"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["is_read"] is True

        count_resp = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {user_token}"})
        assert count_resp.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Отметка всех уведомлений как прочитанных."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        response = await client.patch("/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        assert response.json()["marked_as_read"] >= 1

    @pytest.mark.asyncio
    async def test_delete_notification(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Удаление уведомления."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        response = await client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {user_token}"})
        notification_id = response.json()["items"][0]["id"]

        del_resp = await client.delete(f"/api/v1/notifications/{notification_id}", headers={"Authorization": f"Bearer {user_token}"})
        assert del_resp.status_code == 200

        list_resp = await client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {user_token}"})
        ids = [n["id"] for n in list_resp.json()["items"]]
        assert notification_id not in ids

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client):
        """Без токена доступ запрещён."""
        response = await client.get("/api/v1/notifications/")
        assert response.status_code in (401, 403)
