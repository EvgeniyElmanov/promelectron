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

    async def test_merge_cart_unauthorized(self, client):
        response = await client.post(
            "/api/v1/cart/merge",
            json={"items": [{"product_id": 1, "quantity": 1}]},
        )
        assert response.status_code == 403
