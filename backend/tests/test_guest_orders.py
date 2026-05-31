import pytest


class TestGuestOrdersAPI:
    """Тесты гостевого оформления заказа."""

    @pytest.mark.asyncio
    async def test_create_guest_order_success(self, client, test_product):
        """Гость может оформить заказ."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 2}],
                "shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"},
                "guest_email": "guest@example.com",
                "guest_name": "Иван Гость",
                "guest_phone": "+79990001122",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is None
        assert data["guest_email"] == "guest@example.com"
        assert data["guest_name"] == "Иван Гость"
        assert data["guest_phone"] == "+79990001122"
        assert data["status"] == "pending"
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    @pytest.mark.asyncio
    async def test_create_guest_order_empty_items(self, client):
        """Гость не может оформить заказ с пустой корзиной."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [],
                "guest_email": "guest@example.com",
            },
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_guest_order_invalid_product(self, client):
        """Гость не может оформить заказ с несуществующим товаром."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": 99999, "quantity": 1}],
                "guest_email": "guest@example.com",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_guest_order_insufficient_stock(self, client, test_product):
        """Гость не может оформить заказ при недостатке stock."""
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": test_product.stock + 1}],
                "guest_email": "guest@example.com",
            },
        )
        assert response.status_code == 400
        assert "stock" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_guest_order_reduces_stock(self, client, test_product):
        """После гостевого заказа stock уменьшается."""
        initial_stock = test_product.stock
        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 2}],
                "guest_email": "guest@example.com",
            },
        )
        assert response.status_code == 200

        prod_resp = await client.get(f"/api/v1/products/{test_product.id}")
        assert prod_resp.json()["stock"] == initial_stock - 2

    @pytest.mark.asyncio
    async def test_get_guest_order_success(self, client, test_product):
        """Гость может получить свой заказ по ID и email."""
        create_resp = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "guest_email": "guest@example.com",
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
    async def test_get_guest_order_wrong_email(self, client, test_product):
        """Неверный email — 404."""
        create_resp = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "guest_email": "guest@example.com",
            },
        )
        order_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/orders/guest/{order_id}",
            params={"guest_email": "wrong@example.com"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_guest_order_with_delivery_method(self, client, test_product, test_session):
        """Гостевой заказ с методом доставки."""
        from src.app.models.delivery_method import DeliveryMethod

        dm = DeliveryMethod(
            name="Курьер",
            description="Доставка курьером",
            base_price=300.0,
            estimated_days="1-2",
            is_active=True,
        )
        test_session.add(dm)
        await test_session.commit()
        await test_session.refresh(dm)

        response = await client.post(
            "/api/v1/orders/create-guest",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "shipping_address": {"city": "Москва", "street": "Ленина", "house": "1"},
                "delivery_method_id": dm.id,
                "guest_email": "guest@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["delivery_method_id"] == dm.id
        assert float(data["delivery_price"]) == 300.0
        assert float(data["total_price"]) == float(test_product.price) + 300.0
