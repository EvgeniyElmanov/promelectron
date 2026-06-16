import pytest

from src.app.models.category import Category


class TestCategoriesAPI:
    """Тесты для /api/v1/categories/"""

    @pytest.mark.asyncio
    async def test_list_categories_pagination(self, client, test_session, test_admin):
        """Пагинация: skip и limit работают корректно."""
        for i in range(3):
            test_session.add(Category(name=f"Paginated Category {i}"))
        await test_session.commit()

        response = await client.get("/api/v1/categories/?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 2
        assert data["total"] >= 3

        response = await client.get("/api/v1/categories/?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_categories_filter_by_parent_id(self, client, test_session):
        """Фильтр по parent_id возвращает только прямых потомков."""
        root = Category(name="Root Category")
        test_session.add(root)
        await test_session.commit()
        await test_session.refresh(root)

        child = Category(name="Child Category", parent_id=root.id)
        test_session.add(child)
        await test_session.commit()

        response = await client.get(f"/api/v1/categories/?parent_id={root.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == child.id
        assert data["items"][0]["parent_id"] == root.id

        response = await client.get("/api/v1/categories/?parent_id=-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_categories_search(self, client, test_session):
        """Поиск по названию через query-параметр q."""
        test_session.add_all(
            [
                Category(name="Alpha Phones"),
                Category(name="Beta Laptops"),
            ]
        )
        await test_session.commit()

        response = await client.get("/api/v1/categories/?q=Phones")
        assert response.status_code == 200
        data = response.json()
        names = [c["name"] for c in data["items"]]
        assert "Alpha Phones" in names
        assert "Beta Laptops" not in names

    @pytest.mark.asyncio
    async def test_create_subcategory_as_admin(
        self, client, test_session, test_admin, admin_token
    ):
        """Админ может создать подкатегорию, указав parent_id."""
        root = Category(name="Root For Subcategory")
        test_session.add(root)
        await test_session.commit()
        await test_session.refresh(root)

        response = await client.post(
            "/api/v1/categories/",
            json={"name": "Subcategory", "parent_id": root.id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Subcategory"
        assert data["parent_id"] == root.id
        assert data["product_count"] == 0

    @pytest.mark.asyncio
    async def test_update_category_cycle_protection(
        self, client, test_session, test_admin, admin_token
    ):
        """Нельзя выбрать потомка или саму категорию в качестве родителя."""
        root = Category(name="Root")
        test_session.add(root)
        await test_session.commit()
        await test_session.refresh(root)

        child = Category(name="Child", parent_id=root.id)
        test_session.add(child)
        await test_session.commit()
        await test_session.refresh(child)

        grandchild = Category(name="Grandchild", parent_id=child.id)
        test_session.add(grandchild)
        await test_session.commit()
        await test_session.refresh(grandchild)

        # Попытка сделать родителем потомка — цикл
        response = await client.put(
            f"/api/v1/categories/{root.id}",
            json={"name": "Root", "parent_id": grandchild.id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

        # Попытка сделать категорию родителем самой себя
        response = await client.put(
            f"/api/v1/categories/{child.id}",
            json={"name": "Child", "parent_id": child.id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

        # Корректное перемещение: grandchild под root
        response = await client.put(
            f"/api/v1/categories/{grandchild.id}",
            json={"name": "Grandchild", "parent_id": root.id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == root.id

    @pytest.mark.asyncio
    async def test_category_product_count(self, client, test_product, test_category):
        """В выдаче присутствует счётчик товаров категории."""
        response = await client.get(f"/api/v1/categories/{test_category.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["product_count"] == 1

        response = await client.get("/api/v1/categories/")
        assert response.status_code == 200
        data = response.json()
        category = next(c for c in data["items"] if c["id"] == test_category.id)
        assert category["product_count"] == 1

    @pytest.mark.asyncio
    async def test_create_category_invalid_parent_as_admin(
        self, client, test_admin, admin_token
    ):
        """Создание категории с несуществующим parent_id возвращает 404."""
        response = await client.post(
            "/api/v1/categories/",
            json={"name": "Orphan", "parent_id": 99999},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404
