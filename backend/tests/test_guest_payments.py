from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.app.models.order import Order
from src.app.models.payment import Payment
from src.app.models.recipient import Recipient
from src.app.models.user import PasswordResetToken, User, UserAddress
from src.app.schemas.order import GuestOrderCreate, GuestOrderItemCreate
from src.app.services.order_service import OrderService
from src.app.services.payment_service import PaymentService


def _guest_order_data(test_product, cdek_delivery_payload, email, save_address=False):
    return GuestOrderCreate(
        items=[GuestOrderItemCreate(product_id=test_product.id, quantity=1)],
        cdek_delivery=cdek_delivery_payload,
        guest_email=email,
        recipient_phone="+79990001122",
        recipient_first_name="Иван",
        recipient_last_name="Гость",
        save_address=save_address,
    )


async def _create_guest_order(
    test_session, test_product, cdek_delivery_payload, guest_email, save_address=False
):
    order_data = _guest_order_data(
        test_product, cdek_delivery_payload, guest_email, save_address=save_address
    )
    return await OrderService.create_guest_order(order_data=order_data, db=test_session)


async def _create_guest_payment(
    test_session, order, guest_email, yookassa_payment_id="guest-yookassa-id"
):
    mock_yookassa = AsyncMock(
        return_value={
            "yookassa_payment_id": yookassa_payment_id,
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/guest",
            "amount": order.total_price,
            "created_at": "2026-06-02T12:00:00.000Z",
        }
    )
    with (
        patch(
            "src.app.services.payment_service.YooKassaService.is_configured",
            return_value=True,
        ),
        patch(
            "src.app.services.payment_service.YooKassaService.create_payment",
            mock_yookassa,
        ),
    ):
        return await PaymentService.create_guest_payment(
            order_id=order.id, guest_email=guest_email, db=test_session
        )


class TestGuestPaymentsAPI:
    """Тесты гостевой оплаты и автосоздания пользователя."""

    @pytest.mark.asyncio
    async def test_create_guest_payment_returns_gone(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Создание нового гостевого платежа отключено — 410 Gone."""
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, "guest@example.com"
        )

        response = await client.post(
            f"/api/v1/payments/guest/{order.id}/",
            json={"guest_email": "guest@example.com"},
        )
        assert response.status_code == 410
        assert "disabled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_guest_payment_wrong_email_returns_gone(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Даже с неверным email создание guest-платежа возвращает 410."""
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, "guest@example.com"
        )

        response = await client.post(
            f"/api/v1/payments/guest/{order.id}/",
            json={"guest_email": "wrong@example.com"},
        )
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_webhook_creates_user_from_guest(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """После успешной оплаты гостевого заказа создаётся пользователь."""
        guest_email = "newuser@example.com"
        order = await _create_guest_order(
            test_session,
            test_product,
            cdek_delivery_payload,
            guest_email,
            save_address=True,
        )
        await _create_guest_payment(
            test_session, order, guest_email, yookassa_payment_id="guest-yookassa-id"
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
            patch(
                "src.app.services.payment_service.YooKassaService.capture_payment",
                AsyncMock(),
            ),
            patch(
                "src.app.services.payment_service.EmailService.send_welcome_email",
                mock_send_welcome,
            ),
        ):
            resp = await client.post(
                "/api/v1/payments/yookassa/webhook/", json=webhook_payload
            )
        assert resp.status_code == 200

        # Проверяем, что welcome email отправлен с временным паролем и токеном
        mock_send_welcome.assert_awaited_once()
        call_kwargs = mock_send_welcome.await_args.kwargs
        assert call_kwargs["to"] == "newuser@example.com"
        assert call_kwargs["temp_password"]
        assert call_kwargs["reset_token"]
        assert call_kwargs["frontend_url"]

        # Проверяем, что заказ привязан к пользователю
        result = await test_session.execute(select(Order).where(Order.id == order.id))
        order = result.scalars().first()
        assert order.user_id is not None
        assert order.status == "paid"

        # Проверяем создание пользователя
        user_result = await test_session.execute(
            select(User).where(User.email == guest_email)
        )
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

        # Проверяем создание получателя по умолчанию
        recipient_result = await test_session.execute(
            select(Recipient).where(Recipient.user_id == user.id)
        )
        recipient = recipient_result.scalars().first()
        assert recipient is not None
        assert recipient.first_name == "Иван"
        assert recipient.last_name == "Гость"
        assert recipient.phone == "+79990001122"
        assert recipient.is_default is True

    @pytest.mark.asyncio
    async def test_webhook_links_guest_order_to_existing_user(
        self, client, test_product, cdek_delivery_payload, test_session, test_user
    ):
        """Если пользователь с таким email уже есть, заказ привязывается к нему."""
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, test_user.email
        )
        await _create_guest_payment(
            test_session,
            order,
            test_user.email,
            yookassa_payment_id="guest-yookassa-id",
        )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "guest-yookassa-id",
                "status": "succeeded",
            },
        }

        with patch(
            "src.app.services.payment_service.YooKassaService.capture_payment",
            AsyncMock(),
        ):
            resp = await client.post(
                "/api/v1/payments/yookassa/webhook/", json=webhook_payload
            )
        assert resp.status_code == 200

        result = await test_session.execute(select(Order).where(Order.id == order.id))
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
        guest_email = "nosave@example.com"
        order = await _create_guest_order(
            test_session,
            test_product,
            cdek_delivery_payload,
            guest_email,
            save_address=False,
        )
        await _create_guest_payment(
            test_session, order, guest_email, yookassa_payment_id="guest-yookassa-id"
        )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "guest-yookassa-id",
                "status": "succeeded",
            },
        }

        with patch(
            "src.app.services.payment_service.YooKassaService.capture_payment",
            AsyncMock(),
        ):
            resp = await client.post(
                "/api/v1/payments/yookassa/webhook/", json=webhook_payload
            )
        assert resp.status_code == 200

        user_result = await test_session.execute(
            select(User).where(User.email == guest_email)
        )
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
        guest_email = "mockguest@example.com"
        order = await _create_guest_order(
            test_session,
            test_product,
            cdek_delivery_payload,
            guest_email,
            save_address=True,
        )

        with patch(
            "src.app.services.payment_service.YooKassaService.is_configured",
            return_value=False,
        ):
            await PaymentService.create_guest_payment(
                order_id=order.id, guest_email=guest_email, db=test_session
            )

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order.id}/mock-confirm/",
            json={"guest_email": guest_email},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "paid"

        result = await test_session.execute(select(Order).where(Order.id == order.id))
        order = result.scalars().first()
        assert order.user_id is not None
        assert order.status == "paid"

        user_result = await test_session.execute(
            select(User).where(User.email == guest_email)
        )
        user = user_result.scalars().first()
        assert user is not None

        # Проверяем создание получателя по умолчанию
        recipient_result = await test_session.execute(
            select(Recipient).where(Recipient.user_id == user.id)
        )
        recipient = recipient_result.scalars().first()
        assert recipient is not None
        assert recipient.first_name == "Иван"
        assert recipient.last_name == "Гость"
        assert recipient.is_default is True

    @pytest.mark.asyncio
    async def test_guest_mock_confirm_wrong_email(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Guest mock-confirm с неверным email возвращает 404."""
        guest_email = "mockguest2@example.com"
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, guest_email
        )

        with patch(
            "src.app.services.payment_service.YooKassaService.is_configured",
            return_value=False,
        ):
            await PaymentService.create_guest_payment(
                order_id=order.id, guest_email=guest_email, db=test_session
            )

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order.id}/mock-confirm/",
            json={"guest_email": "wrong@example.com"},
        )
        assert confirm_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_guest_mock_confirm_query_email(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Guest mock-confirm принимает guest_email через query-параметр."""
        guest_email = "mockguest3@example.com"
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, guest_email
        )

        with patch(
            "src.app.services.payment_service.YooKassaService.is_configured",
            return_value=False,
        ):
            await PaymentService.create_guest_payment(
                order_id=order.id, guest_email=guest_email, db=test_session
            )

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order.id}/mock-confirm/",
            params={"guest_email": guest_email},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_create_guest_payment_case_insensitive_email_returns_gone(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Email в другом регистре не меняет ответ отключённого endpoint — 410."""
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, "guest@example.com"
        )

        response = await client.post(
            f"/api/v1/payments/guest/{order.id}/",
            json={"guest_email": "GUEST@EXAMPLE.COM"},
        )
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_guest_mock_confirm_case_insensitive_email(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Подтверждение mock-платежа работает с email в другом регистре."""
        guest_email = "MockGuest@Example.COM"
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, guest_email
        )

        with patch(
            "src.app.services.payment_service.YooKassaService.is_configured",
            return_value=False,
        ):
            await PaymentService.create_guest_payment(
                order_id=order.id, guest_email=guest_email, db=test_session
            )

        confirm_resp = await client.post(
            f"/api/v1/payments/guest/{order.id}/mock-confirm/",
            json={"guest_email": "MOCKGUEST@EXAMPLE.COM"},
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_webhook_links_guest_order_to_existing_user_case_insensitive(
        self, client, test_product, cdek_delivery_payload, test_session, test_user
    ):
        """Если email гостя отличается регистром от существующего пользователя — заказ привязывается."""
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, test_user.email.upper()
        )
        await _create_guest_payment(
            test_session,
            order,
            test_user.email.upper(),
            yookassa_payment_id="guest-yookassa-id",
        )

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "guest-yookassa-id",
                "status": "succeeded",
            },
        }

        with patch(
            "src.app.services.payment_service.YooKassaService.capture_payment",
            AsyncMock(),
        ):
            resp = await client.post(
                "/api/v1/payments/yookassa/webhook/", json=webhook_payload
            )
        assert resp.status_code == 200

        result = await test_session.execute(select(Order).where(Order.id == order.id))
        order = result.scalars().first()
        assert order.user_id == test_user.id
        assert order.status == "paid"

    @pytest.mark.asyncio
    async def test_webhook_guest_payment_canceled_saves_cancellation_details(
        self, client, test_product, cdek_delivery_payload, test_session
    ):
        """Webhook payment.canceled для гостевого заказа сохраняет cancellation_details."""
        guest_email = "canceledguest@example.com"
        order = await _create_guest_order(
            test_session, test_product, cdek_delivery_payload, guest_email
        )
        await _create_guest_payment(
            test_session, order, guest_email, yookassa_payment_id="guest-canceled-id"
        )

        webhook_payload = {
            "event": "payment.canceled",
            "object": {
                "id": "guest-canceled-id",
                "status": "canceled",
                "cancellation_details": {
                    "party": "payment_network",
                    "reason": "insufficient_funds",
                },
            },
        }

        resp = await client.post(
            "/api/v1/payments/yookassa/webhook/", json=webhook_payload
        )
        assert resp.status_code == 200

        result = await test_session.execute(
            select(Payment).where(Payment.order_id == order.id)
        )
        payment = result.scalars().first()
        assert payment.status == "cancelled"
        assert (
            payment.yookassa_metadata.get("cancellation_details", {}).get("reason")
            == "insufficient_funds"
        )

        order_result = await test_session.execute(
            select(Order).where(Order.id == order.id)
        )
        order = order_result.scalars().first()
        assert order.status == "pending"
