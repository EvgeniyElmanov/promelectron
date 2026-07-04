import pytest
from sqlalchemy import select


@pytest.mark.asyncio
class TestCartAPI:
    async def test_get_cart_empty(self, client, user_token, test_user):
        response = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["default_recipient"] is None
        assert data["default_address"] is None

    async def test_add_to_cart_and_get(
        self, client, user_token, test_user, test_product
    ):
        # Add product to cart
        response = await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": 2},
        )
        assert response.status_code == 200
        item = response.json()
        assert item["product_id"] == test_product.id
        assert item["quantity"] == 2

        # Get cart — should include product details
        response = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

        cart_item = data["items"][0]
        assert cart_item["product_id"] == test_product.id
        assert cart_item["quantity"] == 2
        assert cart_item["selected"] is True
        assert cart_item["product"] is not None
        assert cart_item["product"]["name"] == test_product.name
        assert cart_item["product"]["price"] == test_product.price
        assert cart_item["product"]["stock"] == test_product.stock

    async def test_update_cart_item_quantity(
        self, client, user_token, test_user, test_product
    ):
        # Add first
        await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": 1},
        )

        # Get cart to find item id
        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = cart_resp.json()["items"][0]["id"]

        # Update quantity
        response = await client.put(
            f"/api/v1/cart/update/{item_id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"quantity": 5},
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 5

    async def test_remove_from_cart(
        self, client, user_token, test_user, test_product
    ):
        # Add
        await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": 1},
        )

        # Get item id
        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = cart_resp.json()["items"][0]["id"]

        # Remove
        response = await client.delete(
            f"/api/v1/cart/remove/{item_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200

        # Verify empty
        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert cart_resp.json()["items"] == []

    async def test_cart_unauthorized(self, client):
        response = await client.get("/api/v1/cart/")
        assert response.status_code == 403

    async def test_merge_cart(self, client, user_token, test_user, test_product):
        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": test_product.id, "quantity": 2}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["product_id"] == test_product.id

    async def test_merge_cart_sums_quantity(
        self, client, user_token, test_user, test_product
    ):
        # First merge
        await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": test_product.id, "quantity": 2}]},
        )
        # Second merge — should sum
        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": test_product.id, "quantity": 3}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 5

    async def test_merge_cart_multiple_products(
        self, client, user_token, test_user, test_product, test_category, test_session, test_supplier
    ):
        from src.app.models.product import Product
        from src.app.models.supplier import Supplier

        result = await test_session.execute(
            select(Supplier).where(Supplier.user_id == test_supplier.id)
        )
        supplier = result.scalars().first()

        product2 = Product(
            name="Second Product",
            price=199.99,
            stock=5,
            category_id=test_category.id,
            supplier_id=supplier.id,
        )
        test_session.add(product2)
        await test_session.commit()
        await test_session.refresh(product2)

        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "items": [
                    {"product_id": test_product.id, "quantity": 1},
                    {"product_id": product2.id, "quantity": 2},
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    async def test_merge_cart_preserves_selected_for_new_items(
        self, client, user_token, test_user, test_product
    ):
        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": test_product.id, "quantity": 2, "selected": False}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["selected"] is False

    async def test_merge_cart_preserves_existing_selected(
        self, client, user_token, test_user, test_product
    ):
        await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": 1},
        )
        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = cart_resp.json()["items"][0]["id"]

        await client.patch(
            f"/api/v1/cart/select/{item_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"selected": False},
        )

        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": test_product.id, "quantity": 2, "selected": True}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 3
        assert data["items"][0]["selected"] is False

    async def test_merge_cart_default_selected_true_for_new_items(
        self, client, user_token, test_user, test_product
    ):
        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": test_product.id, "quantity": 1}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["selected"] is True

    async def test_merge_cart_unauthorized(self, client):
        response = await client.post(
            "/api/v1/cart/merge",
            json={"items": [{"product_id": 1, "quantity": 1}]},
        )
        assert response.status_code == 403

    async def test_add_to_cart_product_not_found(self, client, user_token, test_user):
        response = await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": 99999, "quantity": 1},
        )
        assert response.status_code == 404

    async def test_add_to_cart_insufficient_stock(
        self, client, user_token, test_user, test_product
    ):
        response = await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": test_product.stock + 1},
        )
        assert response.status_code == 400
        assert "Not enough stock" in response.json()["detail"]

    async def test_update_cart_item_exceeds_stock(
        self, client, user_token, test_user, test_product
    ):
        # Add first
        await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": 1},
        )
        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = cart_resp.json()["items"][0]["id"]

        response = await client.put(
            f"/api/v1/cart/update/{item_id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"quantity": test_product.stock + 1},
        )
        assert response.status_code == 400
        assert "Not enough stock" in response.json()["detail"]

    async def test_merge_cart_product_not_found(self, client, user_token, test_user):
        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": 99999, "quantity": 1}]},
        )
        assert response.status_code == 404

    async def test_merge_cart_insufficient_stock(
        self, client, user_token, test_user, test_product
    ):
        response = await client.post(
            "/api/v1/cart/merge",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"items": [{"product_id": test_product.id, "quantity": test_product.stock + 1}]},
        )
        assert response.status_code == 400
        assert "Not enough stock" in response.json()["detail"]

    async def test_set_cart_item_selected(
        self, client, user_token, test_user, test_product
    ):
        await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": 1},
        )
        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        item_id = cart_resp.json()["items"][0]["id"]

        response = await client.patch(
            f"/api/v1/cart/select/{item_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"selected": False},
        )
        assert response.status_code == 200
        assert response.json()["selected"] is False

        cart_resp = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert cart_resp.json()["items"][0]["selected"] is False

    async def test_select_all_and_deselect_all(
        self, client, user_token, test_user, test_product, test_category, test_session, test_supplier
    ):
        from src.app.models.product import Product
        from src.app.models.supplier import Supplier

        result = await test_session.execute(
            select(Supplier).where(Supplier.user_id == test_supplier.id)
        )
        supplier = result.scalars().first()

        product2 = Product(
            name="Second Product",
            price=199.99,
            stock=5,
            category_id=test_category.id,
            supplier_id=supplier.id,
            is_active=True,
        )
        test_session.add(product2)
        await test_session.commit()
        await test_session.refresh(product2)

        await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": test_product.id, "quantity": 1},
        )
        await client.post(
            "/api/v1/cart/add",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"product_id": product2.id, "quantity": 1},
        )

        response = await client.post(
            "/api/v1/cart/deselect-all/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        assert all(item["selected"] is False for item in response.json()["items"])

        response = await client.post(
            "/api/v1/cart/select-all/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        assert all(item["selected"] is True for item in response.json()["items"])

    async def test_get_cart_defaults(
        self, client, user_token, test_user, test_session
    ):
        from src.app.models.recipient import Recipient
        from src.app.models.user import UserAddress

        recipient = Recipient(
            user_id=test_user.id,
            first_name="Иван",
            last_name="Иванов",
            phone="+79990001122",
            country_code="RU",
            is_default=True,
        )
        address = UserAddress(
            user_id=test_user.id,
            city="Москва",
            street="ул. Ленина",
            house="д. 1",
            is_default=True,
        )
        test_session.add(recipient)
        test_session.add(address)
        await test_session.commit()

        response = await client.get(
            "/api/v1/cart/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["default_recipient"] is not None
        assert data["default_recipient"]["id"] == recipient.id
        assert data["default_address"] is not None
        assert data["default_address"]["id"] == address.id
