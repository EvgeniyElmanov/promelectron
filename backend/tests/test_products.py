import pytest
from io import BytesIO


class TestProductsAPI:
    """Тесты для /api/v1/products/"""

    @pytest.mark.asyncio
    async def test_list_products(self, client, test_product):
        """Получение списка активных товаров с пагинацией."""
        response = await client.get("/api/v1/products/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1
        assert data["items"][0]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_list_products_pagination(self, client, test_session, test_category, test_supplier):
        """Пагинация: limit и skip работают корректно."""
        from tests.conftest import make_product

        # Создаём 5 товаров
        for i in range(5):
            await make_product(
                test_session,
                name=f"Pagination Product {i}",
                price=10.0 + i,
                stock=10,
                supplier_id=test_supplier.id,
                category_id=test_category.id,
                is_active=True,
            )
        await test_session.commit()

        response = await client.get("/api/v1/products/?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5

        response = await client.get("/api/v1/products/?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_products_sort_by_price(self, client, test_session, test_category, test_supplier):
        """Сортировка по цене."""
        from tests.conftest import make_product

        for i, price in enumerate([100.0, 50.0, 150.0]):
            await make_product(
                test_session,
                name=f"Sort Product {i}",
                price=price,
                stock=10,
                supplier_id=test_supplier.id,
                category_id=test_category.id,
                is_active=True,
            )
        await test_session.commit()

        response = await client.get("/api/v1/products/?sort_by=price_asc")
        data = response.json()
        prices = [p["price"] for p in data["items"]]
        # Check that ascending prices appear in order
        filtered = [p for p in prices if p in [50.0, 100.0, 150.0]]
        assert filtered == sorted(filtered)

        response = await client.get("/api/v1/products/?sort_by=price_desc")
        data = response.json()
        prices = [p["price"] for p in data["items"]]
        filtered = [p for p in prices if p in [50.0, 100.0, 150.0]]
        assert filtered == sorted(filtered, reverse=True)

    @pytest.mark.asyncio
    async def test_list_products_filter_by_price(self, client, test_session, test_category, test_supplier):
        """Фильтрация по ценовому диапазону."""
        from tests.conftest import make_product

        for i, price in enumerate([30.0, 60.0, 90.0]):
            await make_product(
                test_session,
                name=f"Filter Product {i}",
                price=price,
                stock=10,
                supplier_id=test_supplier.id,
                category_id=test_category.id,
                is_active=True,
            )
        await test_session.commit()

        response = await client.get("/api/v1/products/?min_price=40&max_price=80")
        data = response.json()
        for p in data["items"]:
            if p["name"].startswith("Filter Product"):
                assert 40 <= p["price"] <= 80

    @pytest.mark.asyncio
    async def test_list_products_search(self, client, test_session, test_category, test_supplier):
        """Поиск по названию и описанию."""
        from tests.conftest import make_product

        await make_product(
            test_session,
            name="Unique Searchable Name",
            description="Some description",
            price=10.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await make_product(
            test_session,
            name="Other Product",
            description="Unique Searchable Description",
            price=20.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await test_session.commit()

        response = await client.get("/api/v1/products/?q=Searchable")
        data = response.json()
        names = [p["name"] for p in data["items"]]
        assert any("Searchable" in n for n in names)

    @pytest.mark.asyncio
    async def test_list_products_filter_by_min_rating(self, client, test_session, test_category, test_supplier, test_user):
        """Фильтрация по минимальному рейтингу."""
        from src.app.models.review import Review
        from tests.conftest import make_product

        p1 = await make_product(
            test_session,
            name="High Rated Product",
            price=100.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        p2 = await make_product(
            test_session,
            name="Low Rated Product",
            price=50.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await test_session.commit()
        await test_session.refresh(p1)
        await test_session.refresh(p2)

        # Create reviews: p1 has avg 4.5, p2 has avg 2.0
        r1 = Review(product_id=p1.id, user_id=test_user.id, rating=5, text="Great")
        r2 = Review(product_id=p1.id, user_id=test_user.id, rating=4, text="Good")
        r3 = Review(product_id=p2.id, user_id=test_user.id, rating=2, text="Bad")
        test_session.add_all([r1, r2, r3])
        await test_session.commit()

        response = await client.get("/api/v1/products/?min_rating=3")
        data = response.json()
        names = [p["name"] for p in data["items"]]
        assert "High Rated Product" in names
        assert "Low Rated Product" not in names

        response = await client.get("/api/v1/products/?min_rating=4.5")
        data = response.json()
        names = [p["name"] for p in data["items"]]
        assert "High Rated Product" in names

    @pytest.mark.asyncio
    async def test_list_products_sort_by_rating(self, client, test_session, test_category, test_supplier, test_user):
        """Сортировка по рейтингу (убывание)."""
        from src.app.models.review import Review
        from tests.conftest import make_product

        p1 = await make_product(
            test_session,
            name="Medium Rated",
            price=100.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        p2 = await make_product(
            test_session,
            name="Top Rated",
            price=50.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await make_product(
            test_session,
            name="No Reviews",
            price=30.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await test_session.commit()
        await test_session.refresh(p1)
        await test_session.refresh(p2)

        r1 = Review(product_id=p1.id, user_id=test_user.id, rating=3, text="Ok")
        r2 = Review(product_id=p2.id, user_id=test_user.id, rating=5, text="Excellent")
        test_session.add_all([r1, r2])
        await test_session.commit()

        response = await client.get("/api/v1/products/?sort_by=rating_desc")
        data = response.json()
        names = [p["name"] for p in data["items"]]
        # Top rated should come before medium rated
        idx_top = names.index("Top Rated")
        idx_medium = names.index("Medium Rated")
        assert idx_top < idx_medium

    @pytest.mark.asyncio
    async def test_list_products_filter_by_category(self, client, test_session, test_category, test_supplier):
        """Фильтрация по категории."""
        from src.app.models.category import Category
        from tests.conftest import make_product

        cat2 = Category(name="Other Category")
        test_session.add(cat2)
        await test_session.commit()
        await test_session.refresh(cat2)

        await make_product(
            test_session,
            name="Cat1 Product",
            price=10.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await make_product(
            test_session,
            name="Cat2 Product",
            price=20.0,
            stock=10,
            supplier_id=test_supplier.id,
            category_id=cat2.id,
            is_active=True,
        )
        await test_session.commit()

        response = await client.get(f"/api/v1/products/?category_id={test_category.id}")
        data = response.json()
        for p in data["items"]:
            if p["name"].startswith("Cat"):
                assert p["category_id"] == test_category.id

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
    async def test_create_product_as_supplier(self, client, test_supplier, test_category):
        """Создание товара поставщиком — успешно."""
        from src.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_supplier.id), "role": test_supplier.role.value})
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
        assert isinstance(data["supplier_id"], int)

    @pytest.mark.asyncio
    async def test_create_product_supplier_not_registered(self, client, test_supplier_user_only, test_category):
        """Создание товара поставщиком без записи в Supplier — 403."""
        from src.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_supplier_user_only.id), "role": test_supplier_user_only.role.value})
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

    @pytest.mark.asyncio
    async def test_upload_product_image(self, client, test_product, test_supplier):
        """Загрузка изображения поставщиком — успешно."""
        from src.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_supplier.id), "role": test_supplier.role.value})
        file_data = BytesIO(b"fake-image-data")
        response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.jpg", file_data, "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["images"]) == 1
        assert "products/" in data["images"][0]
        # Verify WebP variants are returned
        assert "small" in data
        assert "medium" in data
        assert "large" in data
        assert data["small"].endswith("_small.webp")
        assert data["medium"].endswith("_medium.webp")
        assert data["large"].endswith("_large.webp")

    @pytest.mark.asyncio
    async def test_upload_image_unauthorized(self, client, test_product):
        """Загрузка изображения без токена — 401/403."""
        file_data = BytesIO(b"fake-image-data")
        response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.jpg", file_data, "image/jpeg")},
        )
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client, test_product, test_supplier):
        """Загрузка не-изображения — 400."""
        from src.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_supplier.id), "role": test_supplier.role.value})
        file_data = BytesIO(b"not-an-image")
        response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.txt", file_data, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("ext,mime", [
        ("jpg", "image/jpeg"),
        ("jpeg", "image/jpeg"),
        ("png", "image/png"),
        ("webp", "image/webp"),
        ("gif", "image/gif"),
    ])
    async def test_upload_all_image_formats(self, client, test_product, test_supplier, ext, mime):
        """Загрузка всех поддерживаемых форматов изображений."""
        from src.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_supplier.id), "role": test_supplier.role.value})
        file_data = BytesIO(b"fake-image-data")
        response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": (f"test.{ext}", file_data, mime)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["images"]) >= 1
        assert data["images"][-1].endswith(f".{ext}")

    @pytest.mark.asyncio
    async def test_upload_product_image_enqueues_search_index_job(
        self, client, test_session, test_product, test_supplier
    ):
        """После upload фото ставится Job SEARCH_INDEX_PRODUCTS с product_ids=[id]."""
        from sqlalchemy import select

        from src.app.models.job import Job
        from src.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_supplier.id), "role": test_supplier.role.value})
        file_data = BytesIO(b"fake-image-data")
        response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.jpg", file_data, "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
        jobs = result.scalars().all()
        assert len(jobs) == 1
        assert jobs[0].payload["product_ids"] == [test_product.id]
        assert jobs[0].status == "pending"

    @pytest.mark.asyncio
    async def test_delete_product_image_enqueues_search_index_job(
        self, client, test_session, test_product, test_supplier
    ):
        """После delete фото ставится Job SEARCH_INDEX_PRODUCTS с product_ids=[id]."""
        from sqlalchemy import select

        from src.app.models.job import Job
        from src.app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_supplier.id), "role": test_supplier.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        file_data = BytesIO(b"fake-image-data")
        upload_resp = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.jpg", file_data, "image/jpeg")},
            headers=headers,
        )
        assert upload_resp.status_code == 200
        filename = upload_resp.json()["images"][-1].split("/")[-1]

        delete_resp = await client.delete(
            f"/api/v1/products/{test_product.id}/images/{filename}",
            headers=headers,
        )
        assert delete_resp.status_code == 200

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
        jobs = result.scalars().all()
        # один Job от upload, второй от delete
        assert len(jobs) == 2
        for job in jobs:
            assert job.payload["product_ids"] == [test_product.id]
