import pytest


class TestGuestOrdersAPI:
    """Тесты гостевого оформления заказа."""

    @pytest.mark.asyncio
    async def test_create_guest_order_success(self, client, test_product, cdek_delivery_payload):
        """Гость может оформить заказ."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 2}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "guest_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is None
        assert data["guest_email"] == "guest@example.com"
        assert data["guest_name"] is None
        assert data["recipient_first_name"] == "Иван"
        assert data["recipient_last_name"] == "Гость"
        assert data["guest_phone"] == "+79990001122"
        assert data["status"] == "pending"
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["cdek_tariff_code"] == cdek_delivery_payload["tariff_code"]

    @pytest.mark.asyncio
    async def test_create_guest_order_empty_items(self, client, cdek_delivery_payload):
        """Гость не может оформить заказ с пустой корзиной."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "guest_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_guest_order_invalid_product(self, client, cdek_delivery_payload):
        """Гость не может оформить заказ с несуществующим товаром."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": 99999, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "guest_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_guest_order_insufficient_stock(self, client, test_product, cdek_delivery_payload):
        """Гость не может оформить заказ при недостатке stock."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": test_product.stock + 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "guest_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        assert response.status_code == 400
        assert "stock" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_guest_order_reduces_stock(self, client, test_product, cdek_delivery_payload):
        """После гостевого заказа stock уменьшается."""
        initial_stock = test_product.stock
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 2}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "guest_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        assert response.status_code == 200

        prod_resp = await client.get(f"/api/v1/products/{test_product.id}")
        assert prod_resp.json()["stock"] == initial_stock - 2

    @pytest.mark.asyncio
    async def test_get_guest_order_success(self, client, test_product, cdek_delivery_payload):
        """Гость может получить свой заказ по ID и email."""
        create_resp = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "guest_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/orders/guest/{order_id}",
            params={"guest_email": "guest@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id
        assert data["guest_email"] == "guest@example.com"

    @pytest.mark.asyncio
    async def test_get_guest_order_wrong_email(self, client, test_product, cdek_delivery_payload):
        """Неверный email — 404."""
        create_resp = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "guest_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/orders/guest/{order_id}",
            params={"guest_email": "wrong@example.com"},
        )
        assert response.status_code == 404
