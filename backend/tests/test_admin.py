import pytest


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
