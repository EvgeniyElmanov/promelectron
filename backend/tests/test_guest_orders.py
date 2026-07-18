import pytest

from src.app.schemas.order import GuestOrderCreate, GuestOrderItemCreate
from src.app.services.order_service import OrderService


def _build_guest_order_create(
    test_product, cdek_delivery_payload, email="guest@example.com"
):
    return GuestOrderCreate(
        items=[GuestOrderItemCreate(product_id=test_product.id, quantity=1)],
        cdek_delivery=cdek_delivery_payload,
        guest_email=email,
        recipient_phone="+79990001122",
        recipient_first_name="Иван",
        recipient_last_name="Гость",
    )


@pytest.fixture
async def guest_order(test_product, cdek_delivery_payload, test_session):
    """Гостевой заказ, созданный напрямую через сервис (в обход отключённого API)."""
    order_data = _build_guest_order_create(test_product, cdek_delivery_payload)
    order = await OrderService.create_guest_order(
        order_data=order_data, db=test_session
    )
    return order


class TestGuestOrdersAPI:
    """Тесты гостевого оформления заказа."""

    @pytest.mark.asyncio
    async def test_create_guest_order_returns_gone(
        self, client, test_product, cdek_delivery_payload
    ):
        """Создание нового гостевого заказа отключено — 410 Gone."""
        response = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 2}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        assert response.status_code == 410
        assert "disabled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_guest_order_success(self, client, guest_order):
        """Гость может получить свой заказ по ID и email."""
        response = await client.get(
            f"/api/v1/orders/guest/{guest_order.id}/",
            params={"guest_email": "guest@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == guest_order.id
        assert data["guest_email"] == "guest@example.com"

    @pytest.mark.asyncio
    async def test_get_guest_order_wrong_email(self, client, guest_order):
        """Неверный email — 404."""
        response = await client.get(
            f"/api/v1/orders/guest/{guest_order.id}/",
            params={"guest_email": "wrong@example.com"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_guest_order_case_insensitive_email(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Получение гостевого заказа работает с email в другом регистре."""
        order_data = _build_guest_order_create(
            test_product, cdek_delivery_payload, email="guest@example.com"
        )
        order = await OrderService.create_guest_order(
            order_data=order_data, db=test_session
        )

        response = await client.get(
            f"/api/v1/orders/guest/{order.id}/",
            params={"guest_email": "GUEST@EXAMPLE.COM"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == order.id
