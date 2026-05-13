import pytest


class TestProductsAPI:
    """Тесты для /api/v1/products/"""

    @pytest.mark.asyncio
    async def test_list_products(self, client, test_product):
        """Получение списка активных товаров."""
        response = await client.get("/api/v1/products/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, client, test_product):
        """Получение товара по ID."""
        response = await client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_product.id
        assert data["name"] == "Test Product"
        assert data["price"] == 99.99

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, client):
        """Получение несуществующего товара — 404."""
        response = await client.get("/api/v1/products/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_product_unauthorized(self, client):
        """Создание товара без токена — 401."""
        payload = {"name": "New Product", "price": 49.99, "stock": 5}
        response = await client.post("/api/v1/products/", json=payload)
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_product_as_supplier(self, client, test_supplier, test_category, test_session):
        """Создание товара поставщиком — успешно."""
        from server.app.models.supplier import Supplier
        from server.app.utils.auth import create_access_token

        # Создаём Supplier запись для поставщика
        supplier_record = Supplier(
            user_id=test_supplier.id,
            name="Supplier Record",
            description="Test",
            api_key="key123",
            is_active=True,
        )
        test_session.add(supplier_record)
        await test_session.commit()
        await test_session.refresh(supplier_record)

        token = create_access_token(data={"sub": test_supplier.email})
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "Supplier Product",
                "description": "Created by supplier",
                "price": 29.99,
                "stock": 20,
                "category_id": test_category.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Supplier Product"
        assert data["supplier_id"] == supplier_record.id

    @pytest.mark.asyncio
    async def test_create_product_supplier_not_registered(self, client, test_supplier, test_category):
        """Создание товара поставщиком без записи в Supplier — 403."""
        from server.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": test_supplier.email})
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "Supplier Product",
                "description": "Created by supplier",
                "price": 29.99,
                "stock": 20,
                "category_id": test_category.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
