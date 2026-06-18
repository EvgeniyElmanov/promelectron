from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.app.models.order import Order
from src.app.services.cdek_client import CdekAPIError, CdekClient
from src.app.services.cdek_service import CdekService


import json as _json


class FakeResponse:
    def __init__(self, json_data, status_code=200, text=None):
        self._json = json_data
        self.status_code = status_code
        self.text = text if text is not None else (_json.dumps(json_data) if json_data is not None else "")

    def json(self):
        return self._json


class TestCdekClient:
    """Тесты CdekClient."""

    @pytest.mark.asyncio
    async def test_get_token_from_api_and_cache(self, monkeypatch):
        """Токен запрашивается у CDEK и кешируется в Redis."""
        from src.app.core import redis_client as redis_module

        fake_store = {}

        class FakeRedis:
            async def get(self, key):
                return fake_store.get(key)

            async def setex(self, key, ttl, value):
                fake_store[key] = value

        monkeypatch.setattr(redis_module.RedisClient, "get_instance", classmethod(lambda cls: FakeRedis()))

        fake_http = AsyncMock()
        fake_http.post = AsyncMock(return_value=FakeResponse({"access_token": "test-token", "expires_in": 3600}))
        fake_http.request = AsyncMock(return_value=FakeResponse({"tariff_codes": []}))
        monkeypatch.setattr("src.app.services.cdek_client.httpx.AsyncClient", lambda **kwargs: fake_http)

        client = CdekClient(base_url="https://test.cdek.ru", account="acc", secure="sec")
        await client.calculate_tariffs({})
        await client.close()

        assert fake_store.get("cdek:access_token") == "test-token"
        fake_http.post.assert_called_once()
        call_args = fake_http.post.call_args
        assert call_args.kwargs["data"]["grant_type"] == "client_credentials"

    @pytest.mark.asyncio
    async def test_calculate_tariffs(self, monkeypatch):
        """calculate_tariffs возвращает данные от CDEK."""
        fake_http = AsyncMock()
        fake_http.post = AsyncMock(return_value=FakeResponse({"access_token": "tok", "expires_in": 3600}))
        fake_http.request = AsyncMock(return_value=FakeResponse({"tariff_codes": [{"tariff_code": 136}]}))
        monkeypatch.setattr("src.app.services.cdek_client.httpx.AsyncClient", lambda **kwargs: fake_http)

        client = CdekClient(base_url="https://test.cdek.ru", account="acc", secure="sec")
        result = await client.calculate_tariffs({"type": 1})
        await client.close()

        assert result["tariff_codes"][0]["tariff_code"] == 136

    @pytest.mark.asyncio
    async def test_create_order(self, monkeypatch):
        """create_order возвращает entity uuid."""
        fake_http = AsyncMock()
        fake_http.post = AsyncMock(return_value=FakeResponse({"access_token": "tok", "expires_in": 3600}))
        fake_http.request = AsyncMock(return_value=FakeResponse({"entity": {"uuid": "order-uuid"}, "requests": []}))
        monkeypatch.setattr("src.app.services.cdek_client.httpx.AsyncClient", lambda **kwargs: fake_http)

        client = CdekClient(base_url="https://test.cdek.ru", account="acc", secure="sec")
        result = await client.create_order({"type": 1})
        await client.close()

        assert result["entity"]["uuid"] == "order-uuid"

    @pytest.mark.asyncio
    async def test_get_delivery_points(self, monkeypatch):
        """get_delivery_points парсит ответ."""
        fake_http = AsyncMock()
        fake_http.post = AsyncMock(return_value=FakeResponse({"access_token": "tok", "expires_in": 3600}))
        fake_http.request = AsyncMock(return_value=FakeResponse([{"code": "PVZ1"}]))
        monkeypatch.setattr("src.app.services.cdek_client.httpx.AsyncClient", lambda **kwargs: fake_http)

        client = CdekClient(base_url="https://test.cdek.ru", account="acc", secure="sec")
        result = await client.get_delivery_points({"city_code": 44})
        await client.close()

        assert result[0]["code"] == "PVZ1"

    @pytest.mark.asyncio
    async def test_suggest_cities(self, monkeypatch):
        """suggest_cities возвращает список городов."""
        fake_http = AsyncMock()
        fake_http.post = AsyncMock(return_value=FakeResponse({"access_token": "tok", "expires_in": 3600}))
        fake_http.request = AsyncMock(return_value=FakeResponse([{"code": 44, "city": "Москва"}]))
        monkeypatch.setattr("src.app.services.cdek_client.httpx.AsyncClient", lambda **kwargs: fake_http)

        client = CdekClient(base_url="https://test.cdek.ru", account="acc", secure="sec")
        result = await client.suggest_cities("Москва")
        await client.close()

        assert result[0]["city"] == "Москва"

    @pytest.mark.asyncio
    async def test_api_error_raises(self, monkeypatch):
        """Ошибка API превращается в CdekAPIError."""
        fake_http = AsyncMock()
        fake_http.post = AsyncMock(return_value=FakeResponse({"access_token": "tok", "expires_in": 3600}))
        fake_http.request = AsyncMock(return_value=FakeResponse({"message": "bad request"}, status_code=400))
        monkeypatch.setattr("src.app.services.cdek_client.httpx.AsyncClient", lambda **kwargs: fake_http)

        client = CdekClient(base_url="https://test.cdek.ru", account="acc", secure="sec")
        with pytest.raises(CdekAPIError):
            await client.calculate_tariffs({})
        await client.close()


class TestCdekService:
    """Тесты CdekService."""

    def test_build_calculate_payload_with_delivery_point(self):
        """Payload с delivery_point строится корректно."""
        items = [{"product_id": 1, "quantity": 2, "weight_grams": 500, "length_cm": 20, "width_cm": 15, "height_cm": 10}]
        payload = CdekService.build_calculate_payload(items, {"code": 44}, None, "MSK123")
        assert payload["delivery_point"] == "MSK123"
        assert payload["packages"][0]["weight"] == 1000

    def test_build_calculate_payload_with_to_location(self):
        """Payload с to_location строится корректно."""
        items = [{"product_id": 1, "quantity": 1}]
        payload = CdekService.build_calculate_payload(items, {"code": 44}, {"code": 55, "city": "Екб"}, None)
        assert payload["to_location"]["city"] == "Екб"

    def test_build_calculate_payload_missing_address_raises(self):
        """Отсутствие адреса вызывает HTTPException."""
        with pytest.raises(HTTPException):
            CdekService.build_calculate_payload([{"product_id": 1}], {"code": 44}, None, None)

    def test_build_recipient_from_split_name(self):
        """Имя получателя собирается из раздельных полей заказа."""
        order = Order(
            recipient_first_name="Иван",
            recipient_last_name="Гость",
            guest_phone="+79990001122",
        )
        recipient = CdekService._build_recipient(order)
        assert recipient["name"] == "Иван Гость"
        assert recipient["phones"][0]["number"] == "+79990001122"

    def test_build_recipient_fallback_to_user_full_name(self):
        """При отсутствии раздельных имён используется user.full_name."""
        from src.app.models.user import User

        user = User(full_name="Анна Авторизованная", phone="+79990001122")
        order = Order(user=user)
        recipient = CdekService._build_recipient(order)
        assert recipient["name"] == "Анна Авторизованная"
        assert recipient["phones"][0]["number"] == "+79990001122"

    def test_build_recipient_fallback_to_guest_name(self):
        """При отсутствии раздельных имён и пользователя используется guest_name."""
        order = Order(guest_name="Петр Получатель", guest_phone="+79990001122")
        recipient = CdekService._build_recipient(order)
        assert recipient["name"] == "Петр Получатель"

    def test_build_recipient_default_name(self):
        """Если ничего не указано, подставляется дефолтное имя."""
        order = Order()
        recipient = CdekService._build_recipient(order)
        assert recipient["name"] == "Получатель"

    @pytest.mark.asyncio
    async def test_create_cdek_order_already_has_uuid(self, test_order, test_session):
        """Если у заказа уже есть uuid, повторного создания не происходит."""
        test_order.cdek_uuid = "existing-uuid"
        await test_session.commit()

        result = await CdekService.create_cdek_order(test_order, test_session)
        assert result["entity"]["uuid"] == "existing-uuid"

    @pytest.mark.asyncio
    async def test_create_cdek_order_success(self, test_order, test_session, monkeypatch):
        """Успешное создание заказа в CDEK."""
        test_order.cdek_tariff_code = 136
        test_order.cdek_delivery_mode = "PVZ"
        test_order.cdek_delivery_point = "MSK123"
        test_order.cdek_to_location = {"code": 44, "city": "Москва"}
        test_order.recipient_first_name = "Иван"
        test_order.recipient_last_name = "Гость"
        test_order.guest_phone = "+79990001122"
        await test_session.commit()

        captured_payload = {}

        async def fake_create_order(payload):
            captured_payload.update(payload)
            return {"entity": {"uuid": "new-uuid"}, "requests": [{"state": "ACCEPTED"}]}

        fake_client = AsyncMock()
        fake_client.create_order = fake_create_order
        monkeypatch.setattr("src.app.services.cdek_service.CdekClient", lambda: fake_client)

        result = await CdekService.create_cdek_order(test_order, test_session)
        assert result["entity"]["uuid"] == "new-uuid"
        assert captured_payload["recipient"]["name"] == "Иван Гость"

    @pytest.mark.asyncio
    async def test_handle_order_status_webhook_updates_status(self, test_order, test_session):
        """Webhook ORDER_STATUS обновляет статус заказа."""
        test_order.status = "paid"
        await test_session.commit()

        payload = {
            "type": "ORDER_STATUS",
            "attributes": {
                "number": f"order-{test_order.id}",
                "code": "DELIVERED",
            },
        }
        await CdekService.handle_order_status_webhook(payload, test_session)

        result = await test_session.get(Order, test_order.id)
        assert result.status == "delivered"
        assert result.cdek_status == "DELIVERED"


class TestCdekAPI:
    """Тесты API endpoints CDEK."""

    @pytest.mark.asyncio
    async def test_calculate_delivery_endpoint(self, client, test_supplier, supplier_token, monkeypatch):
        """POST /cdek/calculate возвращает тарифы."""
        result = await client.get("/api/v1/supplier/profile", headers={"Authorization": f"Bearer {supplier_token}"})
        supplier_id = result.json()["id"]

        async def fake_calculate(*args, **kwargs):
            return [{"tariff_code": 136, "price": Decimal("350.00")}]

        monkeypatch.setattr("src.app.api.cdek.CdekService.calculate_delivery", staticmethod(fake_calculate))

        response = await client.post(
            "/api/v1/cdek/calculate/",
            json={
                "items": [{"product_id": 1, "quantity": 1, "weight_grams": 500}],
                "supplier_id": supplier_id,
                "delivery_point": "MSK123",
            },
        )
        assert response.status_code == 200
        assert response.json()["tariffs"][0]["tariff_code"] == 136

    @pytest.mark.asyncio
    async def test_get_delivery_points_endpoint(self, client, monkeypatch):
        """GET /cdek/pvz возвращает список ПВЗ."""
        async def fake_get_points(params):
            return [{"code": "PVZ1"}]

        fake_client = AsyncMock()
        fake_client.get_delivery_points = fake_get_points
        fake_client.close = AsyncMock()
        monkeypatch.setattr("src.app.api.cdek.CdekClient", lambda: fake_client)

        response = await client.get("/api/v1/cdek/pvz/?city_code=44")
        assert response.status_code == 200
        assert response.json()[0]["code"] == "PVZ1"

    @pytest.mark.asyncio
    async def test_suggest_cities_endpoint(self, client, monkeypatch):
        """GET /cdek/suggest-cities возвращает города."""
        async def fake_suggest(name, country_code="RU"):
            return [{"code": 44, "city": "Москва"}]

        fake_client = AsyncMock()
        fake_client.suggest_cities = fake_suggest
        fake_client.close = AsyncMock()
        monkeypatch.setattr("src.app.api.cdek.CdekClient", lambda: fake_client)

        response = await client.get("/api/v1/cdek/suggest-cities/?name=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0")
        assert response.status_code == 200
        assert response.json()[0]["city"] == "Москва"

    @pytest.mark.asyncio
    async def test_cdek_webhook_order_status(self, client, test_order, test_session):
        """POST /webhooks/cdek обновляет статус заказа."""
        test_order.status = "paid"
        await test_session.commit()

        response = await client.post(
            "/api/v1/cdek/webhooks/cdek/",
            json={
                "type": "ORDER_STATUS",
                "attributes": {
                    "number": f"order-{test_order.id}",
                    "code": "SHIPPED",
                },
            },
        )
        assert response.status_code == 200

        result = await test_session.get(Order, test_order.id)
        assert result.cdek_status == "SHIPPED"

    @pytest.mark.asyncio
    async def test_widget_service_offices(self, client, monkeypatch):
        """GET /cdek/widget-service/?action=offices проксирует ПВЗ."""
        async def fake_get_points(params):
            return [{"code": "PVZ1"}]

        fake_client = AsyncMock()
        fake_client.get_delivery_points = fake_get_points
        fake_client.close = AsyncMock()
        monkeypatch.setattr("src.app.api.cdek.CdekClient", lambda: fake_client)

        response = await client.get("/api/v1/cdek/widget-service/?action=offices&city_code=44")
        assert response.status_code == 200
        assert response.json()[0]["code"] == "PVZ1"
        assert response.headers["x-service-version"] == "3.x"

    @pytest.mark.asyncio
    async def test_widget_service_calculate(self, client, monkeypatch):
        """POST /cdek/widget-service/?action=calculate проксирует калькулятор."""
        async def fake_calculate(payload):
            return {"tariff_codes": [{"tariff_code": 136}]}

        fake_client = AsyncMock()
        fake_client.calculate_tariffs = fake_calculate
        fake_client.close = AsyncMock()
        monkeypatch.setattr("src.app.api.cdek.CdekClient", lambda: fake_client)

        response = await client.post(
            "/api/v1/cdek/widget-service/?action=calculate",
            json={"type": 1},
        )
        assert response.status_code == 200
        assert response.json()["tariff_codes"][0]["tariff_code"] == 136
        assert response.headers["x-service-version"] == "3.x"

    @pytest.mark.asyncio
    async def test_widget_service_calculate_requires_post(self, client):
        """GET /cdek/widget-service/?action=calculate возвращает 405."""
        response = await client.get("/api/v1/cdek/widget-service/?action=calculate")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_widget_service_unknown_action(self, client):
        """Неизвестный action возвращает 400."""
        response = await client.get("/api/v1/cdek/widget-service/?action=unknown")
        assert response.status_code == 400
