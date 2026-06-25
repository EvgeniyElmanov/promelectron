from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.app.models.order import Order
from src.app.models.user import PasswordResetToken, User, UserAddress


class TestGuestPaymentsAPI:
    """Тесты гостевой оплаты и автосоздания пользователя."""

    @pytest.mark.asyncio
    async def test_create_guest_payment(self, client, test_product, cdek_delivery_payload):
        """Гость может создать платёж для своего заказа."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        expected_amount = Decimal(str(test_product.price)) + Decimal(str(cdek_delivery_payload["price"]))
        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "guest-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": expected_amount,
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            payment_resp = await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "guest@example.com"},
            )

        assert payment_resp.status_code == 200
        data = payment_resp.json()
        assert data["status"] == "pending"
        assert float(data["amount"]) == float(expected_amount)
        assert data["confirmation_url"] == "https://yoomoney.ru/checkout/guest"

    @pytest.mark.asyncio
    async def test_create_guest_payment_wrong_email(self, client, test_product, cdek_delivery_payload):
        """Платёж с неверным guest_email — 404."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        response = await client.post(
            f"/api/v1/payments/guest/{order_id}/",
            json={"guest_email": "wrong@example.com"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_guest_payment_invalid_email(self, client, test_product, cdek_delivery_payload):
        """Невалидный email в запросе на оплату — 422."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        response = await client.post(
            f"/api/v1/payments/guest/{order_id}/",
            json={"guest_email": "not-an-email"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_webhook_creates_user_from_guest(self, client, test_product, cdek_delivery_payload, test_session):
        """После успешной оплаты гостевого заказа создаётся пользователь."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "newuser@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
                "save_address": True,
            },
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "guest-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "newuser@example.com"},
            )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "guest-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }

        mock_send_welcome = AsyncMock(return_value=None)
        with (
            patch("src.app.services.payment_service.YooKassaService.capture_payment", AsyncMock()),
            patch("src.app.services.payment_service.EmailService.send_welcome_email", mock_send_welcome),
        ):
            resp = await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)
        assert resp.status_code == 200

        # Проверяем, что welcome email отправлен с временным паролем и токеном
        mock_send_welcome.assert_awaited_once()
        call_kwargs = mock_send_welcome.await_args.kwargs
        assert call_kwargs["to"] == "newuser@example.com"
        assert call_kwargs["temp_password"]
        assert call_kwargs["reset_token"]
        assert call_kwargs["frontend_url"]

        # Проверяем, что заказ привязан к пользователю
        result = await test_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalars().first()
        assert order.user_id is not None
        assert order.status == "paid"

        # Проверяем создание пользователя
        user_result = await test_session.execute(select(User).where(User.email == "newuser@example.com"))
        user = user_result.scalars().first()
        assert user is not None
        assert user.full_name == "Иван Гость"
        assert user.phone == "+79990001122"
        assert user.hashed_password is not None

        # Проверяем создание токена сброса пароля
        token_result = await test_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
        assert token_result.scalars().first() is not None

        # Проверяем сохранение адреса
        address_result = await test_session.execute(
            select(UserAddress).where(UserAddress.user_id == user.id)
        )
        address = address_result.scalars().first()
        assert address is not None
        assert address.city is not None

    @pytest.mark.asyncio
    async def test_webhook_links_guest_order_to_existing_user(
        self, client, test_product, cdek_delivery_payload, test_session, test_user
    ):
        """Если пользователь с таким email уже есть, заказ привязывается к нему."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": test_user.email,
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "guest-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": test_user.email},
            )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "guest-yookassa-id",
                "status": "succeeded",
            },
        }

        with patch("src.app.services.payment_service.YooKassaService.capture_payment", AsyncMock()):
            resp = await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)
        assert resp.status_code == 200

        result = await test_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalars().first()
        assert order.user_id == test_user.id
        assert order.status == "paid"

        # Новый пользователь не создан
        user_count_result = await test_session.execute(
            select(User).where(User.email == test_user.email)
        )
        assert len(list(user_count_result.scalars().all())) == 1

    @pytest.mark.asyncio
    async def test_webhook_does_not_save_address_without_flag(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Адрес не сохраняется без флага save_address."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "nosave@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
                "save_address": False,
            },
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "guest-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "nosave@example.com"},
            )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "guest-yookassa-id",
                "status": "succeeded",
            },
        }

        with patch("src.app.services.payment_service.YooKassaService.capture_payment", AsyncMock()):
            resp = await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)
        assert resp.status_code == 200

        user_result = await test_session.execute(select(User).where(User.email == "nosave@example.com"))
        user = user_result.scalars().first()
        assert user is not None

        address_result = await test_session.execute(
            select(UserAddress).where(UserAddress.user_id == user.id)
        )
        assert address_result.scalars().first() is None

    @pytest.mark.asyncio
    async def test_guest_mock_confirm_creates_user(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Guest mock-confirm endpoint создаёт пользователя и привязывает заказ."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "mockguest@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Мок",
                "recipient_last_name": "Гость",
                "save_address": True,
            },
        )
        order_id = order_resp.json()["id"]

        with patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=False):
            create_resp = await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "mockguest@example.com"},
            )
        assert create_resp.status_code == 200

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order_id}/mock-confirm/",
            json={"guest_email": "mockguest@example.com"},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "paid"

        result = await test_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalars().first()
        assert order.user_id is not None
        assert order.status == "paid"

        user_result = await test_session.execute(select(User).where(User.email == "mockguest@example.com"))
        user = user_result.scalars().first()
        assert user is not None

    @pytest.mark.asyncio
    async def test_guest_mock_confirm_wrong_email(self, client, test_product, cdek_delivery_payload):
        """Guest mock-confirm с неверным email возвращает 404."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "mockguest2@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Мок",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        with patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=False):
            await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "mockguest2@example.com"},
            )

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order_id}/mock-confirm/",
            json={"guest_email": "wrong@example.com"},
        )
        assert confirm_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_guest_mock_confirm_query_email(self, client, test_product, cdek_delivery_payload):
        """Guest mock-confirm принимает guest_email через query-параметр."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "mockguest3@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Мок",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        with patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=False):
            await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "mockguest3@example.com"},
            )

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order_id}/mock-confirm/",
            params={"guest_email": "mockguest3@example.com"},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_create_guest_payment_case_insensitive_email(
        self, client, test_product, cdek_delivery_payload
    ):
        """Гостевой платёж ищет заказ по email без учёта регистра."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "guest@example.com",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "guest-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            payment_resp = await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "GUEST@EXAMPLE.COM"},
            )

        assert payment_resp.status_code == 200
        assert payment_resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_guest_mock_confirm_case_insensitive_email(
        self, client, test_product, cdek_delivery_payload
    ):
        """Подтверждение mock-платежа работает с email в другом регистре."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": "MockGuest@Example.COM",
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Мок",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        with patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=False):
            create_resp = await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": "mockguest@example.com"},
            )
        assert create_resp.status_code == 200

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order_id}/mock-confirm/",
            json={"guest_email": "MOCKGUEST@EXAMPLE.COM"},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_webhook_links_guest_order_to_existing_user_case_insensitive(
        self, client, test_product, cdek_delivery_payload, test_session, test_user
    ):
        """Если email гостя отличается регистром от существующего пользователя — заказ привязывается."""
        order_resp = await client.post(
            "/api/v1/orders/create-guest/",
            json={
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "cdek_delivery": cdek_delivery_payload,
                "guest_email": test_user.email.upper(),
                "recipient_phone": "+79990001122",
                "recipient_first_name": "Иван",
                "recipient_last_name": "Гость",
            },
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "guest-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(
                f"/api/v1/payments/guest/{order_id}/",
                json={"guest_email": test_user.email.upper()},
            )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "guest-yookassa-id",
                "status": "succeeded",
            },
        }

        with patch("src.app.services.payment_service.YooKassaService.capture_payment", AsyncMock()):
            resp = await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)
        assert resp.status_code == 200

        result = await test_session.execute(select(Order).where(Order.id == order_id))
        order = result.scalars().first()
        assert order.user_id == test_user.id
        assert order.status == "paid"
