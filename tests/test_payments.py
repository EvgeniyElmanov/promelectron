import pytest


class TestPaymentsAPI:
    """Тесты платёжного шлюза (mock)."""

    @pytest.mark.asyncio
    async def test_create_payment(self, client, test_user, user_token, test_product):
        """Создание платежа для заказа."""
        # Сначала создаём корзину и заказ
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create",
            json={"shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_id = order_resp.json()["id"]

        # Создаём платёж
        payment_resp = await client.post(
            f"/api/v1/payments/{order_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert payment_resp.status_code == 200
        data = payment_resp.json()
        assert data["status"] == "pending"
        assert float(data["amount"]) == float(test_product.price)
        assert "payment_id" in data
        assert "confirmation_url" in data

    @pytest.mark.asyncio
    async def test_create_payment_for_nonexistent_order(self, client, test_user, user_token):
        """Платёж для несуществующего заказа — 404."""
        response = await client.post(
            "/api/v1/payments/99999",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_payment_duplicate(self, client, test_user, user_token, test_product):
        """Повторное создание платежа для того же заказа — 400."""
        # Создаём заказ
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create",
            json={"shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        # Создаём платёж
        await client.post(f"/api/v1/payments/{order_id}", headers={"Authorization": f"Bearer {user_token}"})

        # Пытаемся создать платёж снова
        response = await client.post(f"/api/v1/payments/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_confirm_payment(self, client, test_user, user_token, test_product):
        """Подтверждение платежа меняет статус заказа на paid."""
        # Создаём заказ
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create",
            json={"shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        # Создаём платёж
        payment_resp = await client.post(f"/api/v1/payments/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
        payment_id = payment_resp.json()["payment_id"]

        # Подтверждаем
        confirm_resp = await client.post(
            f"/api/v1/payments/{payment_id}/confirm",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert confirm_resp.status_code == 200
        data = confirm_resp.json()
        assert data["status"] == "paid"
        assert data["paid_at"] is not None

        # Проверяем статус заказа
        order_get = await client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
        assert order_get.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_confirm_already_paid(self, client, test_user, user_token, test_product):
        """Повторное подтверждение оплаченного платежа — 400."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create",
            json={"shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        payment_resp = await client.post(f"/api/v1/payments/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
        payment_id = payment_resp.json()["payment_id"]
        await client.post(f"/api/v1/payments/{payment_id}/confirm", headers={"Authorization": f"Bearer {user_token}"})

        # Повторно подтверждаем
        response = await client.post(f"/api/v1/payments/{payment_id}/confirm", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 400
        assert "already paid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_payment(self, client, test_user, user_token, test_product):
        """Получение информации о платеже."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create",
            json={"shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        payment_resp = await client.post(f"/api/v1/payments/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
        payment_id = payment_resp.json()["payment_id"]

        get_resp = await client.get(f"/api/v1/payments/{payment_id}", headers={"Authorization": f"Bearer {user_token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_cancel_payment(self, client, test_user, user_token, test_product):
        """Отмена неоплаченного платежа."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create",
            json={"shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        payment_resp = await client.post(f"/api/v1/payments/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
        payment_id = payment_resp.json()["payment_id"]

        cancel_resp = await client.post(f"/api/v1/payments/{payment_id}/cancel", headers={"Authorization": f"Bearer {user_token}"})
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_paid_payment_fails(self, client, test_user, user_token, test_product):
        """Отмена оплаченного платежа — 400."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create",
            json={"shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"}},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        payment_resp = await client.post(f"/api/v1/payments/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
        payment_id = payment_resp.json()["payment_id"]
        await client.post(f"/api/v1/payments/{payment_id}/confirm", headers={"Authorization": f"Bearer {user_token}"})

        response = await client.post(f"/api/v1/payments/{payment_id}/cancel", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 400
        assert "Cannot cancel paid payment" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_payment_unauthorized(self, client):
        """Без токена доступ к платежам запрещён."""
        response = await client.post("/api/v1/payments/1")
        assert response.status_code in (401, 403)
