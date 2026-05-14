import pytest


class TestAuthAPI:
    """Тесты для аутентификации."""

    @pytest.mark.asyncio
    async def test_register_user(self, client):
        """Регистрация нового пользователя — возвращает токен и user."""
        response = await client.post(
            "/api/v1/register",
            json={"email": "newuser@example.com", "password": "securepass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["role"] == "user"
        assert "id" in data["user"]

    @pytest.mark.asyncio
    async def test_register_with_full_name(self, client):
        """Регистрация с именем."""
        response = await client.post(
            "/api/v1/register",
            json={
                "email": "nameduser@example.com",
                "password": "securepass123",
                "full_name": "Иван Петров",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["full_name"] == "Иван Петров"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user):
        """Регистрация с уже существующим email — 400."""
        response = await client.post(
            "/api/v1/register",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user):
        """Успешный вход — возвращает токен и user."""
        response = await client.post(
            "/api/v1/login",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "testuser@example.com"
        assert data["user"]["role"] == "user"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user):
        """Вход с неверным паролем — 401."""
        response = await client.post(
            "/api/v1/login",
            json={"email": "testuser@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_me(self, client, test_user, user_token):
        """Получение текущего пользователя."""
        response = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_get_me_no_token(self, client):
        """Запрос /me без токена — 403."""
        response = await client.get("/api/v1/me")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_access(self, client, admin_token, test_admin):
        """Доступ к админ-эндпоинту."""
        response = await client.get(
            "/api/v1/admin",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert "admin" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_user_cannot_access_admin(self, client, user_token, test_user):
        """Обычный пользователь не может получить доступ к /admin."""
        response = await client.get(
            "/api/v1/admin",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_profile(self, client, test_user, user_token):
        """Получение профиля через /auth/profile."""
        response = await client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert "created_at" in data
        assert "full_name" in data

    @pytest.mark.asyncio
    async def test_update_profile_name(self, client, test_user, user_token):
        """Обновление имени через PATCH /me."""
        response = await client.patch(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"full_name": "Иван Обновлённый"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Иван Обновлённый"
        assert data["email"] == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_update_profile_email(self, client, test_user, user_token):
        """Обновление email через PATCH /me."""
        response = await client.patch(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"email": "newemail@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

    @pytest.mark.asyncio
    async def test_update_profile_duplicate_email(self, client, test_user, test_admin, user_token):
        """Обновление email на уже существующий — 400."""
        response = await client.patch(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"email": "admin@example.com"},
        )
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_profile_no_token(self, client):
        """PATCH /me без токена — 403."""
        response = await client.patch("/api/v1/me", json={"full_name": "Test"})
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_change_password_success(self, client, test_user, user_token):
        """Успешная смена пароля."""
        response = await client.patch(
            "/api/v1/me/password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"old_password": "password123", "new_password": "newpassword456"},
        )
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]

        # Проверяем вход с новым паролем
        login_resp = await client.post(
            "/api/v1/login",
            json={"email": "testuser@example.com", "password": "newpassword456"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, client, test_user, user_token):
        """Смена пароля с неверным старым паролем — 400."""
        response = await client.patch(
            "/api/v1/me/password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"old_password": "wrongpassword", "new_password": "newpassword456"},
        )
        assert response.status_code == 400
        assert "Incorrect old password" in response.json()["detail"]
