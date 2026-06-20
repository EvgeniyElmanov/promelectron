from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from src.app.models.order import Order
from src.app.services.cdek_client import CdekAPIError, CdekClient
from src.app.services.cdek_service import CdekService


import json as _json

from src.app.core.redis_client import RedisClient


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
    async def test_create_cdek_order_success(self, test_order, test_supplier, test_session, monkeypatch):
        """Успешное создание заказа в CDEK."""
        from src.app.models.supplier import Supplier

        test_order.cdek_tariff_code = 136
        test_order.cdek_delivery_mode = "PVZ"
        test_order.cdek_delivery_point = "MSK123"
        test_order.cdek_to_location = {"code": 44, "city": "Москва"}
        test_order.recipient_first_name = "Иван"
        test_order.recipient_last_name = "Гость"
        test_order.guest_phone = "+79990001122"
        await test_session.commit()

        result = await test_session.execute(select(Supplier).where(Supplier.user_id == test_supplier.id))
        supplier = result.scalars().first()
        supplier.cdek_shipment_point = "MSK123"
        await test_session.commit()

        captured_payload = {}

        async def fake_get_delivery_point(*args):
            return {"code": "MSK123", "location": {"city_code": 44}}

        async def fake_create_order(payload):
            captured_payload.update(payload)
            return {"entity": {"uuid": "new-uuid"}, "requests": [{"state": "ACCEPTED"}]}

        fake_client = AsyncMock()
        fake_client.get_delivery_point = fake_get_delivery_point
        fake_client.create_order = fake_create_order
        monkeypatch.setattr("src.app.services.cdek_service.CdekClient", lambda: fake_client)

        result = await CdekService.create_cdek_order(test_order, test_session)
        assert result["entity"]["uuid"] == "new-uuid"
        assert captured_payload["recipient"]["name"] == "Иван Гость"
        assert captured_payload["from_location"]["code"] == 44

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

    @pytest.mark.asyncio
    async def test_resolve_shipment_city_code_cache_miss(self, test_supplier, test_session, monkeypatch):
        """resolve_shipment_city_code запрашивает ПВЗ и кеширует city_code."""
        from src.app.models.supplier import Supplier

        result = await test_session.execute(select(Supplier).where(Supplier.user_id == test_supplier.id))
        supplier = result.scalars().first()
        supplier.cdek_shipment_point = "MSK123"
        await test_session.commit()

        fake_point = {"code": "MSK123", "location": {"city_code": 44}}

        async def fake_get_delivery_point(*args):
            code = args[-1]
            assert code == "MSK123"
            return fake_point

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_point", fake_get_delivery_point)

        city_code = await CdekService.resolve_shipment_city_code(supplier.id, test_session)
        assert city_code == 44

        cached = await RedisClient.get("cdek:pvz:city:MSK123")
        assert cached == "44"

    @pytest.mark.asyncio
    async def test_resolve_shipment_city_code_cache_hit(self, test_supplier, test_session, monkeypatch):
        """resolve_shipment_city_code возвращает city_code из кэша без запроса к CDEK."""
        from src.app.models.supplier import Supplier

        result = await test_session.execute(select(Supplier).where(Supplier.user_id == test_supplier.id))
        supplier = result.scalars().first()
        supplier.cdek_shipment_point = "MSK123"
        await test_session.commit()

        await RedisClient.set("cdek:pvz:city:MSK123", "55", ttl=3600)

        called = []

        async def fake_get_delivery_point(*args):
            called.append(args[-1])
            return None

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_point", fake_get_delivery_point)

        city_code = await CdekService.resolve_shipment_city_code(supplier.id, test_session)
        assert city_code == 55
        assert not called

    @pytest.mark.asyncio
    async def test_resolve_shipment_city_code_without_pvz(self, test_supplier, test_session):
        """resolve_shipment_city_code возвращает None если ПВЗ не настроен."""
        from src.app.models.supplier import Supplier

        result = await test_session.execute(select(Supplier).where(Supplier.user_id == test_supplier.id))
        supplier = result.scalars().first()
        supplier.cdek_shipment_point = ""
        await test_session.commit()

        city_code = await CdekService.resolve_shipment_city_code(supplier.id, test_session)
        assert city_code is None

    @pytest.mark.asyncio
    async def test_get_cached_pvz_cache_miss(self, monkeypatch):
        """get_cached_pvz запрашивает CDEK и кеширует результат."""
        fake_points = [{"code": "PVZ1", "location": {"city_code": 44}}]

        async def fake_get_delivery_points(self, params):
            assert params == {"city_code": 44, "type": "PVZ"}
            return fake_points

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_points", fake_get_delivery_points)

        points = await CdekService.get_cached_pvz(44, "PVZ")
        assert points == fake_points

        cached = await RedisClient.get("cdek:pvz:city:44:PVZ")
        assert _json.loads(cached) == fake_points

    @pytest.mark.asyncio
    async def test_get_cached_pvz_cache_hit(self, monkeypatch):
        """get_cached_pvz возвращает данные из кэша без запроса к CDEK."""
        fake_points = [{"code": "PVZ1", "location": {"city_code": 44}}]
        await RedisClient.set("cdek:pvz:city:44:PVZ", _json.dumps(fake_points), ttl=3600)

        called = []

        async def fake_get_delivery_points(self, params):
            called.append(params)
            return []

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_points", fake_get_delivery_points)

        points = await CdekService.get_cached_pvz(44, "PVZ")
        assert points == fake_points
        assert not called

    @pytest.mark.asyncio
    async def test_get_cached_pvz_invalid_type_defaults_to_pvz(self, monkeypatch):
        """get_cached_pvz заменяет недопустимый type на PVZ."""
        fake_points = [{"code": "PVZ1", "location": {"city_code": 44}}]

        async def fake_get_delivery_points(self, params):
            assert params["type"] == "PVZ"
            return fake_points

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_points", fake_get_delivery_points)

        points = await CdekService.get_cached_pvz(44, "INVALID")
        assert points == fake_points

    @pytest.mark.asyncio
    async def test_calculate_delivery_uses_city_code_for_pvz_shipment_point(
        self, test_supplier, test_session, monkeypatch
    ):
        """calculate_delivery использует city_code как город отправления, не код ПВЗ."""
        from src.app.models.supplier import Supplier

        result = await test_session.execute(select(Supplier).where(Supplier.user_id == test_supplier.id))
        supplier = result.scalars().first()
        supplier.cdek_shipment_point = "MSK123"
        await test_session.commit()

        async def fake_get_delivery_point(*args):
            return {"code": "MSK123", "location": {"city_code": 44}}

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_point", fake_get_delivery_point)

        called_payloads = []

        async def fake_calculate_tariffs(self, payload):
            called_payloads.append(payload)
            assert payload["from_location"]["code"] == 44
            return {"tariff_codes": [{"tariff_code": 136, "delivery_sum": 350.0}]}

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.calculate_tariffs", fake_calculate_tariffs)

        tariffs = await CdekService.calculate_delivery(
            db=test_session,
            items=[{"product_id": 1, "quantity": 1, "weight_grams": 500}],
            supplier_id=supplier.id,
            to_location={"code": 44},
            delivery_point=None,
        )
        assert len(tariffs) == 1
        assert tariffs[0]["tariff_code"] == 136
        assert len(called_payloads) == 1

    @pytest.mark.asyncio
    async def test_calculate_delivery_retries_with_city_code_on_api_error(
        self, test_supplier, test_session, monkeypatch
    ):
        """calculate_delivery делает fallback retry с city_code при persistent ошибке CDEK."""
        from src.app.models.supplier import Supplier

        result = await test_session.execute(select(Supplier).where(Supplier.user_id == test_supplier.id))
        supplier = result.scalars().first()
        supplier.cdek_shipment_point = "MSK123"
        await test_session.commit()

        async def fake_get_delivery_point(*args):
            return {"code": "MSK123", "location": {"city_code": 44}}

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_point", fake_get_delivery_point)

        calls = []

        async def fake_calculate_tariffs(self, payload):
            calls.append(payload)
            if len(calls) == 1:
                raise CdekAPIError(
                    "sender location not recognized",
                    status_code=400,
                    response_body={"errors": [{"code": "v2_sender_location_not_recognized"}]},
                )
            return {"tariff_codes": [{"tariff_code": 136, "delivery_sum": 350.0}]}

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.calculate_tariffs", fake_calculate_tariffs)

        tariffs = await CdekService.calculate_delivery(
            db=test_session,
            items=[{"product_id": 1, "quantity": 1, "weight_grams": 500}],
            supplier_id=supplier.id,
            to_location={"code": 44},
            delivery_point=None,
        )
        assert len(tariffs) == 1
        assert len(calls) == 2
        assert calls[0]["from_location"]["code"] == 44
        assert calls[1]["from_location"]["code"] == 44


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
    async def test_get_delivery_points_endpoint_cache_miss(self, client, monkeypatch):
        """GET /cdek/pvz возвращает список ПВЗ и кеширует его."""
        async def fake_get_points(self, params):
            assert params == {"city_code": 44, "type": "PVZ"}
            return [{"code": "PVZ1"}]

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_points", fake_get_points)

        response = await client.get("/api/v1/cdek/pvz/?city_code=44")
        assert response.status_code == 200
        assert response.json()[0]["code"] == "PVZ1"

        cached = await RedisClient.get("cdek:pvz:city:44:PVZ")
        assert _json.loads(cached) == [{"code": "PVZ1"}]

    @pytest.mark.asyncio
    async def test_get_delivery_points_endpoint_cache_hit(self, client, monkeypatch):
        """GET /cdek/pvz возвращает ПВЗ из кэша."""
        await RedisClient.set("cdek:pvz:city:44:PVZ", _json.dumps([{"code": "PVZ2"}]), ttl=3600)

        called = []

        async def fake_get_points(self, params):
            called.append(params)
            return []

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_points", fake_get_points)

        response = await client.get("/api/v1/cdek/pvz/?city_code=44")
        assert response.status_code == 200
        assert response.json()[0]["code"] == "PVZ2"
        assert not called

    @pytest.mark.asyncio
    async def test_get_delivery_points_endpoint_invalid_type(self, client):
        """GET /cdek/pvz с недопустимым type возвращает 422."""
        response = await client.get("/api/v1/cdek/pvz/?city_code=44&type=INVALID")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_supplier_city_code_endpoint(self, client, test_supplier, test_session, supplier_token, monkeypatch):
        """GET /cdek/supplier-city-code/{supplier_id}/ возвращает city_code."""
        from src.app.models.supplier import Supplier

        result = await client.get("/api/v1/supplier/profile", headers={"Authorization": f"Bearer {supplier_token}"})
        supplier_id = result.json()["id"]

        result = await test_session.execute(select(Supplier).where(Supplier.id == supplier_id))
        supplier = result.scalars().first()
        supplier.cdek_shipment_point = "MSK123"
        await test_session.commit()

        async def fake_get_delivery_point(*args):
            return {"code": "MSK123", "location": {"city_code": 44}}

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_delivery_point", fake_get_delivery_point)

        response = await client.get(f"/api/v1/cdek/supplier-city-code/{supplier_id}/")
        assert response.status_code == 200
        assert response.json()["city_code"] == 44

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


class TestCdekStatusSync:
    """Тесты периодической синхронизации статусов СДЭК."""

    @pytest.mark.asyncio
    async def test_sync_order_statuses_updates_order(self, test_order, test_session, monkeypatch):
        """sync_order_statuses обновляет статус и трек-номер заказа."""
        test_order.cdek_uuid = "uuid-295"
        test_order.cdek_status = None
        await test_session.commit()

        async def fake_get_order(self, uuid):
            assert uuid == "uuid-295"
            return {
                "entity": {
                    "cdek_number": "1101234567",
                    "statuses": [
                        {"code": "ACCEPTED_AT_SHIPMENT_WAREHOUSE"},
                    ],
                }
            }

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_order", fake_get_order)

        result = await CdekService.sync_order_statuses(test_session)
        assert result == {"checked": 1, "updated": 1}

        await test_session.refresh(test_order)
        assert test_order.cdek_number == "1101234567"
        assert test_order.tracking_number == "1101234567"
        assert test_order.cdek_status == "ACCEPTED_AT_SHIPMENT_WAREHOUSE"
        assert test_order.status == "shipped"

    @pytest.mark.asyncio
    async def test_sync_order_statuses_skips_final_status(self, test_order, test_session, monkeypatch):
        """sync_order_statuses пропускает заказы с финальным статусом."""
        test_order.cdek_uuid = "uuid-delivered"
        test_order.cdek_status = "DELIVERED"
        test_order.status = "delivered"
        await test_session.commit()

        called = []

        async def fake_get_order(self, uuid):
            called.append(uuid)
            return {"entity": {}}

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_order", fake_get_order)

        result = await CdekService.sync_order_statuses(test_session)
        assert result == {"checked": 0, "updated": 0}
        assert not called

    @pytest.mark.asyncio
    async def test_sync_order_statuses_handles_api_error(self, test_order, test_session, monkeypatch):
        """sync_order_statuses продолжает работу при ошибке API для одного заказа."""
        from src.app.services.cdek_client import CdekAPIError

        test_order.cdek_uuid = "uuid-error"
        test_order.cdek_status = None
        await test_session.commit()

        async def fake_get_order(self, uuid):
            raise CdekAPIError("CDEK unavailable")

        monkeypatch.setattr("src.app.services.cdek_service.CdekClient.get_order", fake_get_order)

        result = await CdekService.sync_order_statuses(test_session)
        assert result == {"checked": 1, "updated": 0}
