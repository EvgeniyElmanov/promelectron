import pytest


class TestRecipientsAPI:
    """Тесты CRUD получателей текущего пользователя."""

    @pytest.mark.asyncio
    async def test_list_recipients_empty(self, client, test_user, user_token):
        """Список получателей пуст по умолчанию."""
        response = await client.get(
            "/api/v1/me/recipients/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_recipient(self, client, test_user, user_token):
        """Пользователь может создать получателя."""
        response = await client.post(
            "/api/v1/me/recipients/",
            json={
                "first_name": "Иван",
                "last_name": "Иванов",
                "patronymic": "Иванович",
                "phone": "+79990001122",
                "country_code": "RU",
                "is_default": True,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Иван"
        assert data["last_name"] == "Иванов"
        assert data["patronymic"] == "Иванович"
        assert data["phone"] == "+79990001122"
        assert data["country_code"] == "RU"
        assert data["is_default"] is True
        assert data["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_create_recipient_unauthorized(self, client):
        """Без токена создание получателя запрещено."""
        response = await client.post(
            "/api/v1/me/recipients/",
            json={
                "first_name": "Иван",
                "last_name": "Иванов",
                "phone": "+79990001122",
            },
        )
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_recipients(self, client, test_user, user_token, test_session):
        """Пользователь видит только своих получателей."""
        from src.app.models.recipient import Recipient

        recipient = Recipient(
            user_id=test_user.id,
            first_name="Пётр",
            last_name="Петров",
            phone="+79990002233",
            country_code="RU",
            is_default=False,
        )
        test_session.add(recipient)
        await test_session.commit()

        response = await client.get(
            "/api/v1/me/recipients/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["first_name"] == "Пётр"

    @pytest.mark.asyncio
    async def test_default_flag_resets_others(self, client, test_user, user_token, test_session):
        """При создании is_default=True снимается флаг у других получателей."""
        from src.app.models.recipient import Recipient

        old = Recipient(
            user_id=test_user.id,
            first_name="Старый",
            last_name="Получатель",
            phone="+79990001111",
            country_code="RU",
            is_default=True,
        )
        test_session.add(old)
        await test_session.commit()

        response = await client.post(
            "/api/v1/me/recipients/",
            json={
                "first_name": "Новый",
                "last_name": "Получатель",
                "phone": "+79990002222",
                "is_default": True,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200

        await test_session.refresh(old)
        assert old.is_default is False

    @pytest.mark.asyncio
    async def test_update_recipient(self, client, test_user, user_token, test_session):
        """Пользователь может обновить получателя."""
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

        response = await client.patch(
            f"/api/v1/me/recipients/{recipient.id}/",
            json={"first_name": "Александр", "phone": "+79990003344"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Александр"
        assert data["last_name"] == "Иванов"
        assert data["phone"] == "+79990003344"

    @pytest.mark.asyncio
    async def test_update_other_user_recipient_fails(self, client, test_user, user_token, test_session):
        """Нельзя обновить чужого получателя."""
        from src.app.models.recipient import Recipient
        from src.app.models.user import RoleEnum, User
        from src.app.utils.auth import hash_password

        other = User(
            email="other_user@example.com",
            hashed_password=hash_password("password123"),
            role=RoleEnum.user,
            is_active=True,
        )
        test_session.add(other)
        await test_session.commit()
        await test_session.refresh(other)

        recipient = Recipient(
            user_id=other.id,
            first_name="Чужой",
            last_name="Получатель",
            phone="+79990001122",
            country_code="RU",
            is_default=False,
        )
        test_session.add(recipient)
        await test_session.commit()
        await test_session.refresh(recipient)

        response = await client.patch(
            f"/api/v1/me/recipients/{recipient.id}/",
            json={"first_name": "Александр"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_recipient(self, client, test_user, user_token, test_session):
        """Пользователь может удалить получателя без заказов."""
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

        response = await client.delete(
            f"/api/v1/me/recipients/{recipient.id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_recipient_linked_to_order_fails(
        self, client, test_user, user_token, test_product, cdek_delivery_payload, test_session
    ):
        """Нельзя удалить получателя, связанного с заказом."""
        await client.post(
            "/api/v1/cart/add",
            json={"product_id": test_product.id, "quantity": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_resp = await client.post(
            "/api/v1/orders/create/",
            json={
                "cdek_delivery": cdek_delivery_payload,
                "recipient_first_name": "Иван",
                "recipient_last_name": "Иванов",
                "recipient_phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert order_resp.status_code == 200
        order_data = order_resp.json()
        recipient_id = order_data["recipient"]["id"]

        response = await client.delete(
            f"/api/v1/me/recipients/{recipient_id}/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_set_default_recipient(self, client, test_user, user_token, test_session):
        """Пользователь может назначить получателя по умолчанию."""
        from src.app.models.recipient import Recipient

        r1 = Recipient(
            user_id=test_user.id,
            first_name="Первый",
            last_name="Получатель",
            phone="+79990001111",
            country_code="RU",
            is_default=True,
        )
        r2 = Recipient(
            user_id=test_user.id,
            first_name="Второй",
            last_name="Получатель",
            phone="+79990002222",
            country_code="RU",
            is_default=False,
        )
        test_session.add_all([r1, r2])
        await test_session.commit()
        await test_session.refresh(r2)

        response = await client.post(
            f"/api/v1/me/recipients/{r2.id}/set-default/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

        await test_session.refresh(r1)
        assert r1.is_default is False

    @pytest.mark.asyncio
    async def test_invalid_phone_rejected(self, client, test_user, user_token):
        """Невалидный телефон отклоняется."""
        response = await client.post(
            "/api/v1/me/recipients/",
            json={
                "first_name": "Иван",
                "last_name": "Иванов",
                "phone": "89990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_name_rejected(self, client, test_user, user_token):
        """Имя с цифрами отклоняется."""
        response = await client.post(
            "/api/v1/me/recipients/",
            json={
                "first_name": "Иван123",
                "last_name": "Иванов",
                "phone": "+79990001122",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 422
