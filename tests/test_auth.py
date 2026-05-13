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
