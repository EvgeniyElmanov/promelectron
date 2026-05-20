import pytest


class TestFavoritesAPI:
    @pytest.mark.asyncio
    async def test_add_to_favorites(self, client, test_user, test_product):
        token = create_token(test_user)
        response = await client.post(
            f"/api/v1/favorites/add/{test_product.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == test_product.id
        assert data["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_add_duplicate_favorite(self, client, test_user, test_product):
        token = create_token(test_user)
        await client.post(
            f"/api/v1/favorites/add/{test_product.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.post(
            f"/api/v1/favorites/add/{test_product.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_favorites(self, client, test_user, test_product):
        token = create_token(test_user)
        await client.post(
            f"/api/v1/favorites/add/{test_product.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(
            "/api/v1/favorites/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["product_id"] == test_product.id

    @pytest.mark.asyncio
    async def test_remove_from_favorites(self, client, test_user, test_product):
        token = create_token(test_user)
        await client.post(
            f"/api/v1/favorites/add/{test_product.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.delete(
            f"/api/v1/favorites/remove/{test_product.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify empty
        get_resp = await client.get(
            "/api/v1/favorites/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(get_resp.json()) == 0

    @pytest.mark.asyncio
    async def test_product_detail_shows_favorite(self, client, test_user, test_product):
        token = create_token(test_user)
        await client.post(
            f"/api/v1/favorites/add/{test_product.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(
            f"/api/v1/products/{test_product.id}/detail",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_favorite"] is True


def create_token(user):
    from src.app.utils.auth import create_access_token
    return create_access_token(data={"sub": user.email})
