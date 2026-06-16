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


def _make_oauth_settings(overrides: dict):
    from src.app.core.config import Settings, settings as original
    kwargs = {
        "secret_key": original.secret_key,
        "algorithm": original.algorithm,
        "access_token_expire_minutes": original.access_token_expire_minutes,
        "database_url": original.database_url,
        "google_client_id": original.google_client_id,
        "google_client_secret": original.google_client_secret,
        "yandex_client_id": original.yandex_client_id,
        "yandex_client_secret": original.yandex_client_secret,
        "frontend_url": original.frontend_url,
        "smtp_host": original.smtp_host,
        "smtp_port": original.smtp_port,
        "smtp_user": original.smtp_user,
        "smtp_password": original.smtp_password,
        "smtp_from": original.smtp_from,
        "smtp_tls": original.smtp_tls,
        "redis_url": original.redis_url,
        "api_base_url": original.api_base_url,
        "minio_endpoint": original.minio_endpoint,
        "minio_access_key": original.minio_access_key,
        "minio_secret_key": original.minio_secret_key,
        "minio_bucket": original.minio_bucket,
        "minio_secure": original.minio_secure,
        "onec_api_url": original.onec_api_url,
        "onec_api_key": original.onec_api_key,
        "yookassa_shop_id": original.yookassa_shop_id,
        "yookassa_secret_key": original.yookassa_secret_key,
        "yookassa_webhook_secret": original.yookassa_webhook_secret,
        "yookassa_test_mode": original.yookassa_test_mode,
        "yookassa_vat_code": original.yookassa_vat_code,
        "yookassa_tax_system_code": original.yookassa_tax_system_code,
        "yookassa_receipt_enabled": original.yookassa_receipt_enabled,
        "yookassa_capture_auto": original.yookassa_capture_auto,
        "google_oauth_enabled": original.google_oauth_enabled,
        "cdek_account": original.cdek_account,
        "cdek_secure": original.cdek_secure,
        "cdek_api_url": original.cdek_api_url,
        "cdek_test_mode": original.cdek_test_mode,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


class TestOAuth:
    """Тесты для OAuth авторизации."""

    @pytest.mark.asyncio
    async def test_google_login_url(self, client, monkeypatch):
        """Эндпоинт /auth/google/login возвращает корректный URL."""
        new_settings = _make_oauth_settings({
            "google_client_id": "test-google-client-id",
            "google_client_secret": "test-google-secret",
        })
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)

        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/google/login")
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "accounts.google.com" in data["url"]
        assert "client_id=test-google-client-id" in data["url"]
        assert "response_type=code" in data["url"]
        assert "state=google" in data["url"]

    @pytest.mark.asyncio
    async def test_google_callback_creates_user(self, client, test_session, monkeypatch):
        """Google callback создает нового пользователя и social_account."""
        new_settings = _make_oauth_settings({
            "google_client_id": "test-google-client-id",
            "google_client_secret": "test-google-secret",
        })
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        # Мокаем httpx.AsyncClient
        class FakeResponse:
            def __init__(self, json_data, status_code=200):
                self._json = json_data
                self.status_code = status_code

            def json(self):
                return self._json

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, **kwargs):
                return FakeResponse({"access_token": "fake-google-token"})

            async def get(self, url, **kwargs):
                return FakeResponse({
                    "id": "123456789",
                    "email": "googleuser@example.com",
                    "name": "Google User",
                    "picture": "https://example.com/avatar.jpg",
                })

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        response = await client.get("/api/v1/auth/google/callback?code=fake-code")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "googleuser@example.com"
        assert data["user"]["full_name"] == "Google User"
        assert data["user"]["avatar_url"] == "https://example.com/avatar.jpg"
        assert data["user"]["role"] == "user"

    @pytest.mark.asyncio
    async def test_google_callback_existing_user(self, client, test_user, monkeypatch):
        """Google callback привязывает social_account к существующему пользователю."""
        new_settings = _make_oauth_settings({
            "google_client_id": "test-google-client-id",
            "google_client_secret": "test-google-secret",
        })
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        class FakeResponse:
            def __init__(self, json_data, status_code=200):
                self._json = json_data
                self.status_code = status_code

            def json(self):
                return self._json

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, **kwargs):
                return FakeResponse({"access_token": "fake-google-token"})

            async def get(self, url, **kwargs):
                return FakeResponse({
                    "id": "987654321",
                    "email": test_user.email,
                    "name": "Updated Name",
                    "picture": "https://example.com/new-avatar.jpg",
                })

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        response = await client.get("/api/v1/auth/google/callback?code=fake-code")
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == test_user.id

    @pytest.mark.asyncio
    async def test_unsupported_provider(self, client):
        """Неподдерживаемый провайдер возвращает 400."""
        response = await client.get("/api/v1/auth/facebook/login")
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth_providers(self, client, monkeypatch):
        """Эндпоинт /auth/providers/ возвращает доступность провайдеров."""
        new_settings = _make_oauth_settings({
            "google_client_id": "test-google-client-id",
            "google_client_secret": "test-google-secret",
            "yandex_client_id": "test-yandex-client-id",
            "yandex_client_secret": "test-yandex-secret",
            "google_oauth_enabled": True,
        })
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/providers/")
        assert response.status_code == 200
        data = response.json()
        assert data["google"] is True
        assert data["yandex"] is True

    @pytest.mark.asyncio
    async def test_google_login_disabled(self, client, monkeypatch):
        """Google login возвращает 503, если google_oauth выключен."""
        new_settings = _make_oauth_settings({
            "google_client_id": "test-google-client-id",
            "google_client_secret": "test-google-secret",
            "google_oauth_enabled": False,
        })
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/google/login")
        assert response.status_code == 503
        assert "Google" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_google_callback_disabled(self, client, monkeypatch):
        """Google callback возвращает 503, если google_oauth выключен."""
        new_settings = _make_oauth_settings({
            "google_client_id": "test-google-client-id",
            "google_client_secret": "test-google-secret",
            "google_oauth_enabled": False,
        })
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/google/callback?code=fake-code")
        assert response.status_code == 503
        assert "Google" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth_providers_google_disabled(self, client, monkeypatch):
        """/auth/providers/ отдаёт google=false, если google_oauth выключен."""
        new_settings = _make_oauth_settings({
            "google_client_id": "test-google-client-id",
            "google_client_secret": "test-google-secret",
            "yandex_client_id": "test-yandex-client-id",
            "yandex_client_secret": "test-yandex-secret",
            "google_oauth_enabled": False,
        })
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/providers/")
        assert response.status_code == 200
        data = response.json()
        assert data["google"] is False
        assert data["yandex"] is True
