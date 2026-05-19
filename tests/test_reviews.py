import pytest


class TestReviewsAPI:
    @pytest.mark.asyncio
    async def test_create_review(self, client, test_user, test_product):
        token = create_token(test_user)
        response = await client.post(
            f"/api/v1/reviews/product/{test_product.id}",
            json={"rating": 5, "text": "Отличный товар!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5
        assert data["text"] == "Отличный товар!"
        assert data["product_id"] == test_product.id
        assert data["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_create_review_duplicate(self, client, test_user, test_product):
        token = create_token(test_user)
        # First review
        await client.post(
            f"/api/v1/reviews/product/{test_product.id}",
            json={"rating": 4, "text": "Хорошо"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Duplicate should fail
        response = await client.post(
            f"/api/v1/reviews/product/{test_product.id}",
            json={"rating": 3, "text": "Плохо"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_reviews(self, client, test_user, test_product):
        token = create_token(test_user)
        await client.post(
            f"/api/v1/reviews/product/{test_product.id}",
            json={"rating": 5, "text": "Супер"},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(f"/api/v1/reviews/product/{test_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["rating"] == 5

    @pytest.mark.asyncio
    async def test_delete_review(self, client, test_user, test_product):
        token = create_token(test_user)
        create_resp = await client.post(
            f"/api/v1/reviews/product/{test_product.id}",
            json={"rating": 2, "text": "Так себе"},
            headers={"Authorization": f"Bearer {token}"},
        )
        review_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/reviews/{review_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_product_detail_includes_reviews(self, client, test_user, test_product):
        token = create_token(test_user)
        await client.post(
            f"/api/v1/reviews/product/{test_product.id}",
            json={"rating": 4, "text": "Норм"},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(f"/api/v1/products/{test_product.id}/detail")
        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] == 4.0
        assert data["reviews_count"] == 1
        assert len(data["reviews"]) == 1


def create_token(user):
    from server.app.utils.auth import create_access_token
    return create_access_token(data={"sub": user.email})
