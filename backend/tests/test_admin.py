from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select


class TestAdminDashboard:
    """Тесты админ-дашборда."""

    @pytest.mark.asyncio
    async def test_dashboard_stats_as_admin(self, client, test_admin, admin_token):
        """Админ получает статистику дашборда."""
        response = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_orders" in data
        assert "total_revenue" in data
        assert "total_users" in data
        assert "total_products" in data
        assert isinstance(data["total_orders"], int)
        assert isinstance(data["total_revenue"], float)

    @pytest.mark.asyncio
    async def test_dashboard_stats_as_user_forbidden(self, client, test_user, user_token):
        """Обычный пользователь не может получить статистику."""
        response = await client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dashboard_stats_unauthorized(self, client):
        """Без токена доступ запрещён."""
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_orders_by_day_as_admin(self, client, test_admin, admin_token):
        """Админ получает заказы по дням."""
        response = await client.get(
            "/api/v1/admin/orders-by-day",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 7
        for item in data:
            assert "date" in item
            assert "orders" in item
            assert "revenue" in item

    @pytest.mark.asyncio
    async def test_orders_by_day_with_days_param(self, client, test_admin, admin_token):
        """Параметр days влияет на количество дней."""
        response = await client.get(
            "/api/v1/admin/orders-by-day?days=3",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_top_products_as_admin(self, client, test_admin, admin_token):
        """Админ получает топ товаров."""
        response = await client.get(
            "/api/v1/admin/top-products",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_users_list_as_admin(self, client, test_admin, admin_token, test_user):
        """Админ получает список пользователей."""
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        emails = [u["email"] for u in data]
        assert test_admin.email in emails
        assert test_user.email in emails
        for user in data:
            assert "id" in user
            assert "email" in user
            assert "role" in user
            assert "is_active" in user

    @pytest.mark.asyncio
    async def test_toggle_user_active_as_admin(self, client, test_admin, admin_token, test_user):
        """Админ может заблокировать/разблокировать пользователя."""
        # Блокируем
        response = await client.patch(
            f"/api/v1/admin/users/{test_user.id}/toggle-active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["email"] == test_user.email

        # Разблокируем
        response = await client.patch(
            f"/api/v1/admin/users/{test_user.id}/toggle-active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_toggle_nonexistent_user(self, client, test_admin, admin_token):
        """Попытка заблокировать несуществующего пользователя — 404."""
        response = await client.patch(
            "/api/v1/admin/users/99999/toggle-active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_access_admin_users(self, client, test_user, user_token):
        """Обычный пользователь не может получить список пользователей."""
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_toggle_user(self, client, test_user, user_token):
        """Обычный пользователь не может блокировать других."""
        response = await client.patch(
            f"/api/v1/admin/users/{test_user.id}/toggle-active",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403


class TestAdminUserDetail:
    """Тесты детальной информации о пользователе в админке."""

    @pytest.mark.asyncio
    async def test_get_user_detail_as_admin(self, client, test_admin, admin_token, test_user, test_order):
        """Админ получает детали пользователя с заказами."""
        response = await client.get(
            f"/api/v1/admin/users/{test_user.id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["role"] == "user"
        assert "is_active" in data
        assert "social_accounts" in data
        assert isinstance(data["social_accounts"], list)
        assert "orders" in data
        assert isinstance(data["orders"], list)
        assert len(data["orders"]) >= 1
        order = data["orders"][0]
        assert order["id"] == test_order.id
        assert "items" in order
        assert "recipient" in order
        assert "cdek_order" in order
        assert "hashed_password" not in data
        for key in ("id", "email", "full_name", "first_name", "last_name", "patronymic",
                    "country_code", "phone", "avatar_url", "shipping_address",
                    "role", "email_verified", "created_at"):
            assert key in data

    @pytest.mark.asyncio
    async def test_get_user_detail_as_user_forbidden(self, client, test_user, user_token):
        """Обычный пользователь не может получить детали другого пользователя."""
        response = await client.get(
            f"/api/v1/admin/users/{test_user.id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_detail_not_found(self, client, test_admin, admin_token):
        """Запрос несуществующего пользователя возвращает 404."""
        response = await client.get(
            "/api/v1/admin/users/99999/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_user_detail_no_password_leak(self, client, test_admin, admin_token, test_user):
        """В ответе не должно быть hashed_password."""
        response = await client.get(
            f"/api/v1/admin/users/{test_user.id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert "hashed_password" not in response.json()


class TestAdminOrders:
    """Тесты управления заказами админом."""

    @pytest.mark.asyncio
    async def test_admin_list_orders(self, client, test_admin, admin_token, test_order):
        """Админ получает список всех заказов."""
        response = await client.get(
            "/api/v1/admin/orders",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == test_order.id

    @pytest.mark.asyncio
    async def test_admin_filter_orders_by_status(self, client, test_admin, admin_token, test_order):
        """Фильтрация заказов по статусу."""
        response = await client.get(
            "/api/v1/admin/orders?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for order in data:
            assert order["status"] == "pending"

    @pytest.mark.asyncio
    async def test_admin_update_order_status(self, client, test_admin, admin_token, test_order):
        """Админ обновляет статус заказа."""
        response = await client.put(
            f"/api/v1/admin/orders/{test_order.id}",
            json={"status": "shipped", "tracking_number": "TRACK123"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shipped"
        assert data["tracking_number"] == "TRACK123"

    @pytest.mark.asyncio
    async def test_admin_update_invalid_status(self, client, test_admin, admin_token, test_order):
        """Невалидный статус — 400."""
        response = await client.put(
            f"/api/v1/admin/orders/{test_order.id}",
            json={"status": "invalid_status"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_update_nonexistent_order(self, client, test_admin, admin_token):
        """Обновление несуществующего заказа — 404."""
        response = await client.put(
            "/api/v1/admin/orders/99999",
            json={"status": "shipped"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_list_admin_orders(self, client, test_user, user_token):
        """Обычный пользователь не может получить список всех заказов."""
        response = await client.get(
            "/api/v1/admin/orders",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_ship_paid_order(
        self, client, test_admin, admin_token, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Админ переводит оплаченный заказ в статус shipped."""
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

        response = await client.post(
            f"/api/v1/admin/orders/{order_id}/ship/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shipped"

    @pytest.mark.asyncio
    async def test_admin_ship_pending_order_fails(self, client, test_admin, admin_token, test_user, user_token, test_product, cdek_delivery_payload):
        """Админ не может перевести pending заказ в shipped."""
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

        response = await client.post(
            f"/api/v1/admin/orders/{order_id}/ship/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "Only paid orders can be shipped" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_user_cannot_ship_order(self, client, test_user, user_token, test_order):
        """Обычный пользователь не может подтвердить отправку."""
        response = await client.post(
            f"/api/v1/admin/orders/{test_order.id}/ship/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403


class TestAdminCancelOrder:
    """Тесты отмены заказа админом (POST /admin/orders/{id}/cancel/)."""

    async def _create_paid_order(self, client, user_token, test_product, cdek_delivery_payload) -> int:
        """Создать оплаченный заказ: cart → create → mock payment → webhook succeeded."""
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
        return order_id

    @pytest.mark.asyncio
    async def test_admin_cancel_pending_order(self, client, test_admin, admin_token, test_user, user_token, test_product, cdek_delivery_payload):
        """Админ отменяет pending-заказ: статус, причина, возврат stock."""
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

        response = await client.post(
            f"/api/v1/admin/orders/{order_id}/cancel/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["cancelled_at"] is not None
        assert data["cancellation_reason"] == "admin_cancelled"

        # Stock возвращён
        prod_resp = await client.get(f"/api/v1/products/{test_product.id}")
        assert prod_resp.json()["stock"] == test_product.stock

    @pytest.mark.asyncio
    async def test_admin_cancel_paid_order_with_refund(self, client, test_session, test_admin, admin_token, test_user, user_token, test_product, cdek_delivery_payload):
        """Отмена оплаченного заказа админом: refund в ЮKassa, payment → refunded."""
        from src.app.models.payment import Payment

        order_id = await self._create_paid_order(client, user_token, test_product, cdek_delivery_payload)

        mock_refund = AsyncMock(return_value={
            "refund_id": "test-refund-id",
            "status": "succeeded",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })
        with patch("src.app.services.order_service.YooKassaService.create_refund", mock_refund):
            response = await client.post(
                f"/api/v1/admin/orders/{order_id}/cancel/",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["cancelled_at"] is not None
        assert data["cancellation_reason"] == "admin_cancelled"
        mock_refund.assert_awaited_once()

        result = await test_session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = result.scalars().first()
        assert payment.status == "refunded"
        assert payment.refunded_amount == Decimal(str(data["total_price"]))

        # Stock возвращён
        prod_resp = await client.get(f"/api/v1/products/{test_product.id}")
        assert prod_resp.json()["stock"] == test_product.stock

    @pytest.mark.asyncio
    async def test_admin_cancel_paid_order_refund_failure(self, client, test_session, test_admin, admin_token, test_user, user_token, test_product, cdek_delivery_payload):
        """Сбой refund → 502, заказ НЕ отменяется."""
        from src.app.models.order import Order
        from src.app.models.payment import Payment

        order_id = await self._create_paid_order(client, user_token, test_product, cdek_delivery_payload)

        mock_refund = AsyncMock(side_effect=Exception("YooKassa unavailable"))
        with patch("src.app.services.order_service.YooKassaService.create_refund", mock_refund):
            response = await client.post(
                f"/api/v1/admin/orders/{order_id}/cancel/",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 502
        assert "Refund could not be processed" in response.json()["detail"]

        result = await test_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalars().first()
        assert order.status == "paid"

        payment_result = await test_session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = payment_result.scalars().first()
        assert payment.status != "refunded"

    @pytest.mark.asyncio
    async def test_admin_cancel_shipped_order_fails(self, client, test_admin, admin_token, test_user, user_token, test_product, cdek_delivery_payload):
        """Отмена отправленного заказа — 400."""
        order_id = await self._create_paid_order(client, user_token, test_product, cdek_delivery_payload)
        await client.post(
            f"/api/v1/admin/orders/{order_id}/ship/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response = await client.post(
            f"/api/v1/admin/orders/{order_id}/cancel/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "Order cannot be cancelled" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_cancel_already_cancelled_order_fails(self, client, test_admin, admin_token, test_order):
        """Повторная отмена заказа — 400."""
        response = await client.post(
            f"/api/v1/admin/orders/{test_order.id}/cancel/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        response = await client.post(
            f"/api/v1/admin/orders/{test_order.id}/cancel/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "Order cannot be cancelled" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_cancel_nonexistent_order(self, client, test_admin, admin_token):
        """Отмена несуществующего заказа — 404."""
        response = await client.post(
            "/api/v1/admin/orders/99999/cancel/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_cancel_order_via_admin(self, client, test_user, user_token, test_order):
        """Обычный пользователь не может отменить заказ через admin endpoint — 403."""
        response = await client.post(
            f"/api/v1/admin/orders/{test_order.id}/cancel/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cancel_order_unauthorized(self, client, test_order):
        """Без токена доступ запрещён."""
        response = await client.post(f"/api/v1/admin/orders/{test_order.id}/cancel/")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_admin_cancel_order_calls_cdek_cancel(self, client, test_session, test_admin, admin_token, test_order):
        """При наличии cdek_uuid вызывается CdekService.cancel_cdek_order."""
        from src.app.models.cdek_order import CdekOrder

        result = await test_session.execute(select(CdekOrder).where(CdekOrder.order_id == test_order.id))
        cdek_order = result.scalars().first()
        cdek_order.cdek_uuid = "test-cdek-uuid-123"
        await test_session.commit()

        mock_cdek_cancel = AsyncMock(return_value={"entity": {"uuid": "test-cdek-uuid-123"}})
        with patch("src.app.services.order_service.CdekService.cancel_cdek_order", mock_cdek_cancel):
            response = await client.post(
                f"/api/v1/admin/orders/{test_order.id}/cancel/",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        mock_cdek_cancel.assert_awaited_once_with("test-cdek-uuid-123")

    @pytest.mark.asyncio
    async def test_admin_cancel_order_cdek_failure_does_not_block(self, client, test_session, test_admin, admin_token, test_order):
        """Сбой отмены в CDEK не блокирует локальную отмену заказа."""
        from src.app.models.cdek_order import CdekOrder

        result = await test_session.execute(select(CdekOrder).where(CdekOrder.order_id == test_order.id))
        cdek_order = result.scalars().first()
        cdek_order.cdek_uuid = "test-cdek-uuid-456"
        await test_session.commit()

        mock_cdek_cancel = AsyncMock(side_effect=Exception("CDEK refuses: order already ACCEPTED"))
        with patch("src.app.services.order_service.CdekService.cancel_cdek_order", mock_cdek_cancel):
            response = await client.post(
                f"/api/v1/admin/orders/{test_order.id}/cancel/",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        mock_cdek_cancel.assert_awaited_once_with("test-cdek-uuid-456")


class TestAdminFeatureFlags:
    """Тесты управления feature flags в админке."""

    @pytest.mark.asyncio
    async def test_admin_list_feature_flags(self, client, test_admin, admin_token):
        """Админ получает список feature flags."""
        response = await client.get(
            "/api/v1/admin/feature-flags",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(f["name"] == "google_oauth" for f in data)
        for flag in data:
            assert "name" in flag
            assert "enabled" in flag
            assert "source" in flag

    @pytest.mark.asyncio
    async def test_admin_toggle_feature_flag(self, client, test_admin, admin_token):
        """Админ может включить/выключить feature flag."""
        response = await client.patch(
            "/api/v1/admin/feature-flags/google_oauth",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "google_oauth"
        assert data["enabled"] is False
        assert data["source"] == "redis"

        # Включаем обратно
        response = await client.patch(
            "/api/v1/admin/feature-flags/google_oauth",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is True

    @pytest.mark.asyncio
    async def test_user_cannot_access_feature_flags(self, client, test_user, user_token):
        """Обычный пользователь не может управлять фичатоглами."""
        response = await client.get(
            "/api/v1/admin/feature-flags",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

        response = await client.patch(
            "/api/v1/admin/feature-flags/google_oauth",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_unknown_feature_flag(self, client, test_admin, admin_token):
        """Попытка переключить неизвестный флаг — 400."""
        response = await client.patch(
            "/api/v1/admin/feature-flags/unknown_flag",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "Unknown feature flag" in response.json()["detail"]
