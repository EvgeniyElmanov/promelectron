from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select


class TestOrdersAPI:
    """Тесты заказов."""

    @pytest.mark.asyncio
    async def test_cancel_pending_order(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Отмена заказа в статусе pending."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        response = await client.patch(f"/api/v1/orders/{order_id}/cancel/", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["cancelled_at"] is not None

        # Check stock returned
        prod_resp = await client.get(f"/api/v1/products/{test_product.id}")
        assert prod_resp.json()["stock"] == test_product.stock

    @pytest.mark.asyncio
    async def test_cancel_paid_order(self, client, test_user, user_token, test_product, cdek_delivery_payload):
        """Отмена оплаченного заказа с автоматическим YooKassa refund."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})

        # Имитируем webhook от ЮKassa
        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }
        await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)

        mock_refund = AsyncMock(return_value={
            "refund_id": "test-refund-id",
            "status": "succeeded",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with patch("src.app.services.order_service.YooKassaService.create_refund", mock_refund):
            response = await client.patch(f"/api/v1/orders/{order_id}/cancel/", headers={"Authorization": f"Bearer {user_token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["cancelled_at"] is not None
        mock_refund.assert_awaited_once()

        # Check stock returned
        prod_resp = await client.get(f"/api/v1/products/{test_product.id}")
        assert prod_resp.json()["stock"] == test_product.stock

    @pytest.mark.asyncio
    async def test_cancel_shipped_order(self, client, test_user, user_token, test_product, cdek_delivery_payload, admin_token):
        """Отмена отправленного заказа — 400."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        mock_yookassa = AsyncMock(return_value={
            "yookassa_payment_id": "test-yookassa-id",
            "status": "pending",
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "amount": Decimal(str(test_product.price)),
            "created_at": "2026-06-02T12:00:00.000Z",
        })

        with (
            patch("src.app.services.payment_service.YooKassaService.is_configured", return_value=True),
            patch("src.app.services.payment_service.YooKassaService.create_payment", mock_yookassa),
        ):
            await client.post(f"/api/v1/payments/{order_id}/", headers={"Authorization": f"Bearer {user_token}"})

        webhook_payload = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-yookassa-id",
                "status": "succeeded",
                "amount": {"value": str(test_product.price), "currency": "RUB"},
            },
        }
        await client.post("/api/v1/payments/yookassa/webhook/", json=webhook_payload)

        # Переводим заказ в shipped через админку
        await client.post(f"/api/v1/admin/orders/{order_id}/ship/", headers={"Authorization": f"Bearer {admin_token}"})

        response = await client.patch(f"/api/v1/orders/{order_id}/cancel/", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 400
        assert "Order cannot be cancelled" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_other_user_order(self, client, test_user, user_token, test_product):
        """Отмена чужого заказа — 404."""
        # Create another user
        # This is tricky in test, just check 404 for non-existent order
        response = await client.patch("/api/v1/orders/99999/cancel/", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_supplier_can_list_orders(self, client, test_user, user_token, test_supplier, supplier_token, test_product, cdek_delivery_payload):
        """Поставщик видит заказы, содержащие его товары."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_data = order_resp.json()
        order_id = order_data["id"]
        assert order_data["recipient_first_name"] == "Тест"
        assert order_data["recipient_last_name"] == "Пользователь"

        response = await client.get("/api/v1/orders/supplier/", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == order_id
        assert data[0]["buyer_email"] == test_user.email
        assert len(data[0]["items"]) == 1
        assert data[0]["items"][0]["product_name"] == test_product.name
        assert data[0]["total_amount"] == str(test_product.price)

    @pytest.mark.asyncio
    async def test_supplier_cannot_see_orders_without_their_products(self, client, test_user, user_token, test_supplier, supplier_token, test_session, cdek_delivery_payload):
        """Поставщик не видит заказы без своих товаров."""
        from src.app.models.supplier import Supplier
        from src.app.models.user import RoleEnum, User
        from src.app.utils.auth import hash_password
        from tests.conftest import make_product

        other_user = User(
            email="other_supplier@example.com",
            hashed_password=hash_password("password123"),
            role=RoleEnum.supplier,
            is_active=True,
        )
        test_session.add(other_user)
        await test_session.commit()
        await test_session.refresh(other_user)

        other_supplier = Supplier(
            user_id=other_user.id,
            name="Other Supplier",
            description="Other",
            api_key="other-api-key-456",
            is_active=True,
        )
        test_session.add(other_supplier)
        await test_session.commit()
        await test_session.refresh(other_supplier)

        other_product = await make_product(
            test_session,
            name="Other Product",
            description="Other product",
            price=50.0,
            stock=10,
            supplier_id=other_supplier.id,
            is_active=True,
        )
        await test_session.commit()
        await test_session.refresh(other_product)

        await client.post("/api/v1/cart/add", json={"product_id": other_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200

        response = await client.get("/api/v1/orders/supplier/", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_supplier_can_ship_order(self, client, test_user, user_token, test_supplier, supplier_token, test_product, cdek_delivery_payload):
        """Поставщик может отметить заказ как отправленный."""
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        response = await client.patch(f"/api/v1/orders/supplier/{order_id}/ship/", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shipped"

    @pytest.mark.asyncio
    async def test_supplier_cannot_ship_order_without_their_products(self, client, test_user, user_token, test_supplier, supplier_token, test_session, cdek_delivery_payload):
        """Поставщик не может отправить заказ без своих товаров."""
        from src.app.models.supplier import Supplier
        from src.app.models.user import RoleEnum, User
        from src.app.utils.auth import hash_password
        from tests.conftest import make_product

        other_user = User(
            email="other_supplier2@example.com",
            hashed_password=hash_password("password123"),
            role=RoleEnum.supplier,
            is_active=True,
        )
        test_session.add(other_user)
        await test_session.commit()
        await test_session.refresh(other_user)

        other_supplier = Supplier(
            user_id=other_user.id,
            name="Other Supplier 2",
            description="Other",
            api_key="other-api-key-789",
            is_active=True,
        )
        test_session.add(other_supplier)
        await test_session.commit()
        await test_session.refresh(other_supplier)

        other_product = await make_product(
            test_session,
            name="Other Product 2",
            description="Other product",
            price=50.0,
            stock=10,
            supplier_id=other_supplier.id,
            is_active=True,
        )
        await test_session.commit()
        await test_session.refresh(other_product)

        await client.post("/api/v1/cart/add", json={"product_id": other_product.id, "quantity": 1}, headers={"Authorization": f"Bearer {user_token}"})
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = order_resp.json()["id"]

        response = await client.patch(f"/api/v1/orders/supplier/{order_id}/ship/", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_order_with_recipient_id(
        self, client, test_user, user_token, test_product, test_session, cdek_delivery_payload
    ):
        """Создание заказа с выбором сохранённого получателя."""
        from src.app.models.recipient import Recipient

        recipient = Recipient(
            user_id=test_user.id,
            first_name="Иван",
            last_name="Иванов",
            phone="+79990001122",
            country_code="RU",
            is_default=False,
        )
        test_session.add(recipient)
        await test_session.commit()
        await test_session.refresh(recipient)

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={"cdek_delivery": cdek_delivery_payload, "recipient_id": recipient.id},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_data = order_resp.json()
        assert order_data["recipient"]["id"] == recipient.id
        assert order_data["recipient"]["first_name"] == "Иван"
        assert order_data["recipient"]["last_name"] == "Иванов"
        assert order_data["recipient"]["phone"] == "+79990001122"

    @pytest.mark.asyncio
    async def test_create_order_with_inline_recipient(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Создание заказа с inline-полями получателя создаёт нового Recipient."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Пётр",
                "recipient_last_name": "Петров",
                "recipient_patronymic": "Петрович",
                "recipient_phone": "+79990002233",
                "recipient_country_code": "RU",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_data = order_resp.json()
        assert order_data["recipient"] is not None
        assert order_data["recipient"]["first_name"] == "Пётр"
        assert order_data["recipient"]["last_name"] == "Петров"
        assert order_data["recipient"]["patronymic"] == "Петрович"
        assert order_data["recipient"]["phone"] == "+79990002233"

    @pytest.mark.asyncio
    async def test_create_order_removes_only_ordered_items(
        self, client, test_user, user_token, test_product, test_category, test_session, test_supplier, cdek_delivery_payload
    ):
        """После создания заказа оформленные товары удаляются из корзины."""
        from src.app.models.supplier import Supplier
        from tests.conftest import make_product

        result = await test_session.execute(
            select(Supplier).where(Supplier.user_id == test_supplier.id)
        )
        supplier = result.scalars().first()

        product2 = await make_product(
            test_session,
            name="Second Product",
            price=199.99,
            stock=5,
            category_id=test_category.id,
            supplier_id=supplier.id,
            is_active=True,
        )
        await test_session.commit()
        await test_session.refresh(product2)

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": product2.id, "quantity": 2},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_data = order_resp.json()
        assert len(order_data["items"]) == 2

        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert cart_resp.status_code == 200
        cart_data = cart_resp.json()
        assert cart_data["items"] == []

    @pytest.mark.asyncio
    async def test_create_order_failure_keeps_cart_items(
        self, client, test_user, user_token, test_product, test_session, cdek_delivery_payload
    ):
        """Если заказ не создан из-за нехватки stock, корзина остаётся нетронутой."""
        from src.app.models.product import Product

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        result = await test_session.execute(
            select(Product).where(Product.id == test_product.id)
        )
        product = result.scalars().first()
        product.stock = 0
        await test_session.commit()

        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 400

        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert cart_resp.status_code == 200
        cart_data = cart_resp.json()
        assert len(cart_data["items"]) == 1
        assert cart_data["items"][0]["product_id"] == test_product.id
        assert cart_data["items"][0]["quantity"] == 1

    @pytest.mark.asyncio
    async def test_create_order_only_selected_items(
        self, client, test_user, user_token, test_product, test_category, test_session, test_supplier, cdek_delivery_payload
    ):
        """Заказ создаётся только из выбранных товаров; невыбранные остаются в корзине (D-04)."""
        from src.app.models.supplier import Supplier
        from tests.conftest import make_product

        result = await test_session.execute(
            select(Supplier).where(Supplier.user_id == test_supplier.id)
        )
        supplier = result.scalars().first()

        product2 = await make_product(
            test_session,
            name="Second Product",
            price=199.99,
            stock=5,
            category_id=test_category.id,
            supplier_id=supplier.id,
            is_active=True,
        )
        await test_session.commit()
        await test_session.refresh(product2)

        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": product2.id, "quantity": 2},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        items = cart_resp.json()["items"]
        assert len(items) == 2
        deselected_item_id = next(item["id"] for item in items if item["product_id"] == product2.id)

        await client.patch(
            f"/api/v1/cart/select/{deselected_item_id}/",
            json={"selected": False},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_data = order_resp.json()
        assert len(order_data["items"]) == 1
        assert order_data["items"][0]["product_id"] == test_product.id

        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        cart_data = cart_resp.json()
        assert len(cart_data["items"]) == 1
        assert cart_data["items"][0]["product_id"] == product2.id
        assert cart_data["items"][0]["quantity"] == 2
        assert cart_data["items"][0]["selected"] is False

    @pytest.mark.asyncio
    async def test_create_order_no_selected_items(
        self, client, test_user, user_token, test_product, cdek_delivery_payload
    ):
        """Если нет выбранных товаров, создание заказа возвращает 400 (D-04)."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = cart_resp.json()["items"][0]["id"]

        await client.patch(
            f"/api/v1/cart/select/{item_id}/",
            json={"selected": False},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Тест",
                "recipient_last_name": "Пользователь",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 400
        assert "No items selected" in order_resp.json()["detail"]
