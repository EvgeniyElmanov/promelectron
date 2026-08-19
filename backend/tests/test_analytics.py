import pytest
from sqlalchemy import select

from src.app.models.order import Order, OrderItem
from src.app.models.product import Product
from src.app.models.supplier import Supplier
from src.app.models.user import RoleEnum, User
from src.app.utils.auth import hash_password


class TestSupplierAnalytics:
    """Тесты аналитики поставщика."""

    @pytest.mark.asyncio
    async def test_supplier_analytics_basic(self, client, test_user, user_token, test_supplier, supplier_token, test_product, test_session, cdek_delivery_payload):
        """Поставщик получает аналитику по своим товарам."""
        # Создаём заказ с товаром поставщика
        await client.post("/api/v1/cart/add", json={"product_id": test_product.id, "quantity": 2}, headers={"Authorization": f"Bearer {user_token}"})
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
        order_id = order_resp.json()["id"]

        # Обновляем статус заказа на delivered через прямой доступ к БД
        order_result = await test_session.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalars().first()
        order.status = "delivered"
        await test_session.commit()

        response = await client.get("/api/v1/analytics/supplier", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 200
        data = response.json()

        assert "kpi" in data
        assert "orders_by_day" in data
        assert "top_products" in data

        kpi = data["kpi"]
        assert kpi["total_orders"] == 1
        assert kpi["delivered_orders"] == 1
        assert kpi["pending_orders"] == 0
        assert kpi["shipped_orders"] == 0
        assert kpi["total_revenue"] == pytest.approx(199.98, 0.01)
        assert kpi["total_products"] == 1

        assert len(data["orders_by_day"]) == 30
        today_count = sum(1 for d in data["orders_by_day"] if d["count"] > 0)
        assert today_count >= 1

        assert len(data["top_products"]) == 1
        assert data["top_products"][0]["product_name"] == test_product.name
        assert data["top_products"][0]["total_sold"] == 2
        assert data["top_products"][0]["revenue"] == pytest.approx(199.98, 0.01)

    @pytest.mark.asyncio
    async def test_supplier_analytics_isolation(self, client, test_user, user_token, test_supplier, supplier_token, test_session, cdek_delivery_payload):
        """Аналитика изолирована по поставщикам."""

        # Создаём второго поставщика с товаром и заказом
        other_user = User(
            email="other_supplier_analytics@example.com",
            hashed_password=hash_password("password123"),
            role=RoleEnum.supplier,
            is_active=True,
        )
        test_session.add(other_user)
        await test_session.commit()
        await test_session.refresh(other_user)

        other_supplier = Supplier(
            user_id=other_user.id,
            name="Other Supplier Analytics",
            description="Other",
            api_key="other-analytics-key-456",
            is_active=True,
        )
        test_session.add(other_supplier)
        await test_session.commit()
        await test_session.refresh(other_supplier)

        other_product = Product(
            name="Other Product Analytics",
            description="Other product",
            price=50.0,
            stock=10,
            supplier_id=other_supplier.id,
            is_active=True,
        )
        test_session.add(other_product)
        await test_session.commit()
        await test_session.refresh(other_product)

        # Создаём заказ с товаром другого поставщика
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
        order_id = order_resp.json()["id"]

        # Заказ delivered
        order_result = await test_session.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalars().first()
        order.status = "delivered"
        await test_session.commit()

        # Проверяем, что наш поставщик не видит заказ другого поставщика
        response = await client.get("/api/v1/analytics/supplier", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 200
        data = response.json()

        assert data["kpi"]["total_orders"] == 0
        assert data["kpi"]["total_revenue"] == 0.0
        assert len(data["top_products"]) == 0

    @pytest.mark.asyncio
    async def test_supplier_analytics_unauthorized(self, client):
        """Без токена доступ запрещён."""
        response = await client.get("/api/v1/analytics/supplier")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_supplier_analytics_user_forbidden(self, client, test_user, user_token):
        """Обычный пользователь не может получить аналитику поставщика."""
        response = await client.get("/api/v1/analytics/supplier", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_supplier_analytics_multiple_statuses(self, client, test_user, user_token, test_supplier, supplier_token, test_product, test_session, cdek_delivery_payload):
        """KPI считает заказы по разным статусам."""
        # Создаём 3 заказа с разными статусами
        for i in range(3):
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
            order_id = order_resp.json()["id"]

            order_result = await test_session.execute(select(Order).where(Order.id == order_id))
            order = order_result.scalars().first()
            if i == 0:
                order.status = "pending"
            elif i == 1:
                order.status = "shipped"
            else:
                order.status = "delivered"
        await test_session.commit()

        response = await client.get("/api/v1/analytics/supplier", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 200
        data = response.json()

        kpi = data["kpi"]
        assert kpi["total_orders"] == 3
        assert kpi["pending_orders"] == 1
        assert kpi["shipped_orders"] == 1
        assert kpi["delivered_orders"] == 1

    @pytest.mark.asyncio
    async def test_supplier_analytics_top_products_limit(self, client, test_user, user_token, test_supplier, supplier_token, test_product, test_category, test_session):
        """Top products ограничен 5 элементами."""

        # Создаём 6 товаров для поставщика
        result = await test_session.execute(select(Supplier).where(Supplier.user_id == test_supplier.id))
        supplier = result.scalars().first()

        products = []
        for i in range(6):
            product = Product(
                name=f"Product {i}",
                description="Test",
                price=10.0 * (i + 1),
                stock=10,
                supplier_id=supplier.id,
                category_id=test_category.id,
                is_active=True,
            )
            test_session.add(product)
            products.append(product)
        await test_session.commit()
        for p in products:
            await test_session.refresh(p)

        # Создаём заказы на каждый товар
        for i, product in enumerate(products):
            # Очищаем корзину перед каждым заказом — на всякий случай напрямую создаём заказ
            order = Order(
                user_id=test_user.id,
                total_price=product.price,
                status="delivered",
                shipping_address="Москва",
            )
            test_session.add(order)
            await test_session.commit()
            await test_session.refresh(order)

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=i + 1,
                price_at_time=product.price,
            )
            test_session.add(order_item)
        await test_session.commit()

        response = await client.get("/api/v1/analytics/supplier", headers={"Authorization": f"Bearer {supplier_token}"})
        assert response.status_code == 200
        data = response.json()

        assert len(data["top_products"]) == 5
        # Самый продаваемый — Product 5 (quantity=6)
        assert data["top_products"][0]["product_name"] == "Product 5"
        assert data["top_products"][0]["total_sold"] == 6
