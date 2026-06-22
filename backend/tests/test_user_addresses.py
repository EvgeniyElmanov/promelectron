import pytest

from src.app.models.user import UserAddress


class TestUserAddressesAPI:
    """Тесты CRUD адресов пользователя."""

    @pytest.mark.asyncio
    async def test_create_address(self, client, test_user, user_token, test_session):
        """Авторизованный пользователь может создать адрес."""
        response = await client.post(
            "/api/v1/users/me/addresses/",
            json={
                "label": "Дом",
                "city": "Москва",
                "street": "Ленина",
                "house": "1",
                "apartment": "10",
                "postal_code": "123456",
                "is_default": True,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Москва"
        assert data["street"] == "Ленина"
        assert data["house"] == "1"
        assert data["apartment"] == "10"
        assert data["is_default"] is True
        assert data["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_create_address_unauthorized(self, client):
        """Без токена создание адреса запрещено."""
        response = await client.post(
            "/api/v1/users/me/addresses/",
            json={"city": "Москва", "is_default": False},
        )
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_addresses(self, client, test_user, user_token, test_session):
        """Пользователь может получить список своих адресов."""
        addr = UserAddress(
            user_id=test_user.id,
            label="Работа",
            city="Санкт-Петербург",
            country="Россия",
            is_default=False,
        )
        test_session.add(addr)
        await test_session.commit()

        response = await client.get(
            "/api/v1/users/me/addresses/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["city"] == "Санкт-Петербург"

    @pytest.mark.asyncio
    async def test_default_address_flag_resets_others(
        self, client, test_user, user_token, test_session
    ):
        """При создании is_default=True снимается флаг с других адресов."""
        old = UserAddress(
            user_id=test_user.id,
            label="Старый",
            city="Москва",
            country="Россия",
            is_default=True,
        )
        test_session.add(old)
        await test_session.commit()

        response = await client.post(
            "/api/v1/users/me/addresses/",
            json={
                "label": "Новый",
                "city": "Казань",
                "is_default": True,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200

        await test_session.refresh(old)
        assert old.is_default is False
