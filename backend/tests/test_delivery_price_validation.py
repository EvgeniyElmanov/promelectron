"""Регрессия по issue #211: цена доставки из тела запроса без валидации.

До фикса эти тесты ПАДАЮТ, демонстрируя уязвимость: заказ с отрицательной
ценой доставки создаётся, и total_price уходит ниже стоимости товаров
(вплоть до отрицательной суммы в ЮKassa).
"""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.app.schemas.order import GuestOrderCreate, GuestOrderItemCreate
from src.app.services.cdek_client import CdekAPIError
from src.app.services.order_service import OrderService

_CDEK_SERVICE_BINDING = "src.app.services.order_service.CdekService"


def _fake_cdek_service(calculate_delivery):
    """Собрать стаб CdekService с заданной calculate_delivery."""

    class _Fake:
        @staticmethod
        async def cancel_cdek_order(cdek_uuid):
            return None

    _Fake.calculate_delivery = staticmethod(calculate_delivery)
    return _Fake


async def _calculate_raises_cdek_error(db, items, supplier_id, to_location, delivery_point):
    raise CdekAPIError("CDEK unavailable", status_code=500)


async def _calculate_raises_unexpected(db, items, supplier_id, to_location, delivery_point):
    raise RuntimeError("unexpected backend failure")


async def _calculate_other_tariff(db, items, supplier_id, to_location, delivery_point):
    from decimal import Decimal

    return [{"tariff_code": 999, "tariff_name": "Иной тариф", "price": Decimal("350.00")}]


async def _calculate_empty(db, items, supplier_id, to_location, delivery_point):
    return []


@pytest.fixture
def negative_cdek_delivery_payload(cdek_delivery_payload):
    return {**cdek_delivery_payload, "price": "-500.00"}


class TestDeliveryPriceValidation:
    """Отрицательная цена доставки отклоняется на обоих путях создания заказа."""

    @pytest.mark.asyncio
    async def test_create_order_rejects_negative_delivery_price(
        self, client, test_user, user_token, test_product, negative_cdek_delivery_payload, test_session
    ):
        """Авторизованный путь: POST /orders/create/ с price < 0 → 422, заказ не создан."""
        from sqlalchemy import select

        from src.app.models.order import Order

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        response = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": negative_cdek_delivery_payload,
                "recipient_first_name": "Пётр",
                "recipient_last_name": "Петров",
                "recipient_phone": "+79990002233",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 422, (
            f"Заказ с отрицательной ценой доставки должен отклоняться, "
            f"получен {response.status_code}: {response.text[:300]}"
        )

        result = await test_session.execute(select(Order).where(Order.user_id == test_user.id))
        assert result.scalars().first() is None, "Заказ с отрицательной доставкой не должен сохраняться"

    @pytest.mark.asyncio
    async def test_create_guest_order_rejects_negative_delivery_price(
        self, test_product, negative_cdek_delivery_payload, test_session
    ):
        """Гостевой путь: price < 0 отклоняется схемой (ValidationError по cdek_delivery.price)."""
        with pytest.raises(ValidationError) as exc_info:
            GuestOrderCreate(
                items=[GuestOrderItemCreate(product_id=test_product.id, quantity=1)],
                cdek_delivery=negative_cdek_delivery_payload,
                guest_email="guest@example.com",
                recipient_phone="+79990001122",
                recipient_first_name="Иван",
                recipient_last_name="Гость",
            )
        assert any(
            e.get("loc") == ("cdek_delivery", "price") for e in exc_info.value.errors()
        ), f"Ошибка должна относиться к полю cdek_delivery.price: {exc_info.value.errors()}"

    @pytest.mark.asyncio
    async def test_create_order_rejects_oversized_delivery_price(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """S001: мусорно-большая цена ('1E+1000', 32-значная) → 422 на HTTP-пути."""
        for oversized in ("1E+1000", "99999999999999999999999999999999.99"):
            response = await client.post(
                "/api/v1/orders/create/",
                json={
                    "cdek_delivery": {**cdek_delivery_payload, "price": oversized},
                    "recipient_first_name": "Пётр",
                    "recipient_last_name": "Петров",
                    "recipient_phone": "+79990002233",
                },
                headers={"Authorization": f"Bearer {user_token}"},
            )
            assert response.status_code == 422, (
                f"price={oversized} должен отклоняться схемой, "
                f"получен {response.status_code}: {response.text[:300]}"
            )


@pytest.fixture
def mismatched_cdek_delivery_payload(cdek_delivery_payload):
    return {**cdek_delivery_payload, "price": "1.00"}


class TestDeliveryPriceServerRecalculation:
    """Серверная сверка цены доставки с расчётом СДЭК (S-02/S-03/S-05/S-06)."""

    async def _create_order(
        self, client, user_token, test_product, cdek_delivery, test_session
    ):
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        return await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery,
                "recipient_first_name": "Пётр",
                "recipient_last_name": "Петров",
                "recipient_phone": "+79990002233",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

    def _guest_order_data(self, test_product, cdek_delivery):
        return GuestOrderCreate(
            items=[GuestOrderItemCreate(product_id=test_product.id, quantity=1)],
            cdek_delivery=cdek_delivery,
            guest_email="guest@example.com",
            recipient_phone="+79990001122",
            recipient_first_name="Иван",
            recipient_last_name="Гость",
        )

    @pytest.mark.asyncio
    async def test_create_order_rejects_mismatched_delivery_price(
        self, client, test_user, user_token, test_product, mismatched_cdek_delivery_payload, test_session
    ):
        """S-02: заниженная цена → 409, заказ не создан, stock не изменён (auth)."""
        from sqlalchemy import select

        from src.app.models.order import Order

        stock_before = test_product.stock
        response = await self._create_order(
            client, user_token, test_product, mismatched_cdek_delivery_payload, test_session
        )
        assert response.status_code == 409, (
            f"Расходящаяся цена доставки должна отклоняться, "
            f"получен {response.status_code}: {response.text[:300]}"
        )
        assert "устарела" in response.json()["detail"]

        result = await test_session.execute(select(Order).where(Order.user_id == test_user.id))
        assert result.scalars().first() is None, "Заказ с расходящейся доставкой не должен сохраняться"
        await test_session.rollback()
        await test_session.refresh(test_product)
        assert test_product.stock == stock_before, "Stock не должен меняться при отклонённом заказе"

    @pytest.mark.asyncio
    async def test_create_order_rejects_inflated_delivery_price(
        self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session
    ):
        """S-02: завышенная цена тоже отклоняется (сверка симметрична)."""
        inflated = {**cdek_delivery_payload, "price": "999.00"}
        response = await self._create_order(client, user_token, test_product, inflated, test_session)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_guest_order_rejects_mismatched_delivery_price(
        self, test_product, mismatched_cdek_delivery_payload, test_session
    ):
        """S-02/S-04: гостевой сервис — HTTPException(409), stock не изменён."""
        stock_before = test_product.stock
        order_data = self._guest_order_data(test_product, mismatched_cdek_delivery_payload)
        with pytest.raises(HTTPException) as exc_info:
            await OrderService.create_guest_order(order_data=order_data, db=test_session)
        assert exc_info.value.status_code == 409
        await test_session.rollback()
        await test_session.refresh(test_product)
        assert test_product.stock == stock_before

    @pytest.mark.asyncio
    async def test_create_order_accepts_matching_delivery_price(
        self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session
    ):
        """S-03: совпадающая цена → 201, total_price = items + серверная цена."""
        from decimal import Decimal

        response = await self._create_order(
            client, user_token, test_product, cdek_delivery_payload, test_session
        )
        assert response.status_code == 200, response.text[:300]
        data = response.json()
        assert Decimal(str(data["total_price"])) == Decimal("99.99") + Decimal("350.00")
        assert Decimal(str(data["cdek_order"]["price"])) == Decimal("350.00")

    @pytest.mark.asyncio
    async def test_create_guest_order_accepts_matching_delivery_price(
        self, test_product, cdek_delivery_payload, test_session
    ):
        """S-03/S-04: гостевой сервис — заказ создан с серверной ценой."""
        from decimal import Decimal

        order_data = self._guest_order_data(test_product, cdek_delivery_payload)
        order = await OrderService.create_guest_order(order_data=order_data, db=test_session)
        assert Decimal(str(order.total_price)) == Decimal("99.99") + Decimal("350.00")

    @pytest.mark.asyncio
    async def test_create_order_returns_503_when_cdek_unavailable(
        self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session, monkeypatch
    ):
        """S-05: CdekAPIError при пересчёте → 503, заказ не создан (fail-closed)."""
        from sqlalchemy import select

        from src.app.models.order import Order

        monkeypatch.setattr(_CDEK_SERVICE_BINDING, _fake_cdek_service(_calculate_raises_cdek_error))
        response = await self._create_order(
            client, user_token, test_product, cdek_delivery_payload, test_session
        )
        assert response.status_code == 503
        result = await test_session.execute(select(Order).where(Order.user_id == test_user.id))
        assert result.scalars().first() is None

    @pytest.mark.asyncio
    async def test_create_guest_order_returns_503_when_cdek_unavailable(
        self, test_product, cdek_delivery_payload, test_session, monkeypatch
    ):
        """S-05/S-04: гостевой сервис — HTTPException(503)."""
        monkeypatch.setattr(_CDEK_SERVICE_BINDING, _fake_cdek_service(_calculate_raises_cdek_error))
        order_data = self._guest_order_data(test_product, cdek_delivery_payload)
        with pytest.raises(HTTPException) as exc_info:
            await OrderService.create_guest_order(order_data=order_data, db=test_session)
        assert exc_info.value.status_code == 503
        await test_session.rollback()

    @pytest.mark.asyncio
    async def test_create_order_returns_503_on_unexpected_recalculation_error(
        self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session, monkeypatch
    ):
        """S002: не-httpx исключение из calculate_delivery (RedisError и пр.) → 503, не 500."""
        from sqlalchemy import select

        from src.app.models.order import Order

        monkeypatch.setattr(_CDEK_SERVICE_BINDING, _fake_cdek_service(_calculate_raises_unexpected))
        response = await self._create_order(
            client, user_token, test_product, cdek_delivery_payload, test_session
        )
        assert response.status_code == 503
        result = await test_session.execute(select(Order).where(Order.user_id == test_user.id))
        assert result.scalars().first() is None

    @pytest.mark.asyncio
    async def test_create_order_rejects_unavailable_tariff(
        self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session, monkeypatch
    ):
        """S-06: tariff_code отсутствует в серверном расчёте → 409."""
        monkeypatch.setattr(_CDEK_SERVICE_BINDING, _fake_cdek_service(_calculate_other_tariff))
        response = await self._create_order(
            client, user_token, test_product, cdek_delivery_payload, test_session
        )
        assert response.status_code == 409
        assert "устарела" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_order_rejects_empty_tariff_list(
        self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session, monkeypatch
    ):
        """S-06 (edge): пустой список тарифов от СДЭК → 409."""
        monkeypatch.setattr(_CDEK_SERVICE_BINDING, _fake_cdek_service(_calculate_empty))
        response = await self._create_order(
            client, user_token, test_product, cdek_delivery_payload, test_session
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_guest_order_rejects_unavailable_tariff(
        self, test_product, cdek_delivery_payload, test_session, monkeypatch
    ):
        """S-06/S-04: гостевой сервис — HTTPException(409)."""
        monkeypatch.setattr(_CDEK_SERVICE_BINDING, _fake_cdek_service(_calculate_other_tariff))
        order_data = self._guest_order_data(test_product, cdek_delivery_payload)
        with pytest.raises(HTTPException) as exc_info:
            await OrderService.create_guest_order(order_data=order_data, db=test_session)
        assert exc_info.value.status_code == 409
        await test_session.rollback()
