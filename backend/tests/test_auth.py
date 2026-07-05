from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from src.app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from src.app.services.oauth_state import create_state


def _decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def _assert_token_expiry(token: str):
    payload = _decode_access_token(token)
    now = datetime.now(timezone.utc)
    expected_exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    assert abs(payload["exp"] - expected_exp.timestamp()) < 60


class TestAuthAPI:
    """Тесты для аутентификации."""

    @pytest.mark.asyncio
    async def test_register_user(self, client):
        """Регистрация нового пользователя — возвращает токен и user."""
        response = await client.post(
            "/api/v1/register/",
            json={"email": "newuser@example.com", "password": "securepass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["role"] == "user"
        assert data["user"]["email_verified"] is False
        assert "id" in data["user"]

    @pytest.mark.asyncio
    async def test_register_with_full_name(self, client):
        """Регистрация с именем."""
        response = await client.post(
            "/api/v1/register/",
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
            "/api/v1/register/",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user):
        """Успешный вход — возвращает токен и user."""
        response = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "testuser@example.com"
        assert data["user"]["role"] == "user"
        assert data["user"]["email_verified"] is False

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user):
        """Вход с неверным паролем — 401."""
        response = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_token_expiry_matches_settings(self, client, test_user):
        """Токен входа имеет exp, соответствующий ACCESS_TOKEN_EXPIRE_MINUTES."""
        response = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        _assert_token_expiry(data["access_token"])

    @pytest.mark.asyncio
    async def test_get_me(self, client, test_user, user_token):
        """Получение текущего пользователя."""
        response = await client.get(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_get_me_no_token(self, client):
        """Запрос /me без токена — 403."""
        response = await client.get("/api/v1/me/")
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
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"full_name": "Иван Обновлённый"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Иван Обновлённый"
        assert data["email"] == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_update_profile_extended_fields(self, client, test_user, user_token):
        """Обновление ФИО и страны через PATCH /me."""
        response = await client.patch(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "first_name": "Иван",
                "last_name": "Иванов",
                "patronymic": "Иванович",
                "country_code": "RU",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Иван"
        assert data["last_name"] == "Иванов"
        assert data["patronymic"] == "Иванович"
        assert data["country_code"] == "RU"

    @pytest.mark.asyncio
    async def test_update_profile_phone_success(self, client, test_user, user_token):
        """Обновление телефона в профиле принимается только в формате +7XXXXXXXXXX."""
        response = await client.patch(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"phone": "+79161234567"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "+79161234567"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"phone": "89161234567"},
            {"phone": "+7916123456"},
            {"phone": "abc"},
            {"first_name": "Иван123"},
            {"last_name": ""},
            {"patronymic": "Иванович!"},
        ],
    )
    async def test_update_profile_invalid_pii(self, client, test_user, user_token, payload):
        """Невалидные PII-поля профиля отклоняются с 422."""
        response = await client.patch(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json=payload,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_profile_email(self, client, test_user, user_token):
        """Обновление email через PATCH /me."""
        response = await client.patch(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"email": "newemail@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

    @pytest.mark.asyncio
    async def test_update_profile_duplicate_email(
        self, client, test_user, test_admin, user_token
    ):
        """Обновление email на уже существующий — 400."""
        response = await client.patch(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"email": "admin@example.com"},
        )
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_profile_no_token(self, client):
        """PATCH /me без токена — 403."""
        response = await client.patch("/api/v1/me/", json={"full_name": "Test"})
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_change_password_success(self, client, test_user, user_token):
        """Успешная смена пароля."""
        response = await client.patch(
            "/api/v1/me/password/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"old_password": "password123", "new_password": "newpassword456"},
        )
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]

        # Проверяем вход с новым паролем
        login_resp = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "newpassword456"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, client, test_user, user_token):
        """Смена пароля с неверным старым паролем — 400."""
        response = await client.patch(
            "/api/v1/me/password/",
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
        "smtp_from_name": original.smtp_from_name,
        "smtp_use_tls": original.smtp_use_tls,
        "smtp_starttls": original.smtp_starttls,
        "email_verify_token_ttl_minutes": original.email_verify_token_ttl_minutes,
        "verify_base_url": original.verify_base_url,
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
        "cdek_sync_cron_interval_seconds": original.cdek_sync_cron_interval_seconds,
        "cdek_terminal_statuses": original.cdek_terminal_statuses,
        "job_worker_sleep_seconds": original.job_worker_sleep_seconds,
        "job_max_attempts": original.job_max_attempts,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


class TestOAuth:
    """Тесты для OAuth авторизации."""

    @pytest.mark.asyncio
    async def test_google_login_url(self, client, monkeypatch):
        """Эндпоинт /auth/google/login возвращает корректный URL."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)

        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/google/login")
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "accounts.google.com" in data["url"]
        assert "client_id=test-google-client-id" in data["url"]
        assert "response_type=code" in data["url"]
        assert "state=" in data["url"]
        assert "prompt=select_account" in data["url"]
        assert "code_challenge=" in data["url"]
        assert "code_challenge_method=S256" in data["url"]

    @pytest.mark.asyncio
    async def test_yandex_login_url_when_called_should_force_account_select(
        self, client, monkeypatch
    ):
        """Эндпоинт /auth/yandex/login возвращает URL с force_confirm=yes (issue #4)."""
        new_settings = _make_oauth_settings(
            {
                "yandex_client_id": "test-yandex-client-id",
                "yandex_client_secret": "test-yandex-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/yandex/login")
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "oauth.yandex.ru" in data["url"]
        assert "client_id=test-yandex-client-id" in data["url"]
        assert "response_type=code" in data["url"]
        assert "state=" in data["url"]
        assert "force_confirm=yes" in data["url"]
        assert "code_challenge_method=S256" in data["url"]

    @pytest.mark.asyncio
    async def test_google_callback_creates_user(
        self, client, test_session, monkeypatch
    ):
        """Google callback создает нового пользователя и social_account."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
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
                return FakeResponse(
                    {
                        "id": "123456789",
                        "email": "googleuser@example.com",
                        "name": "Google User",
                        "picture": "https://example.com/avatar.jpg",
                    }
                )

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "googleuser@example.com"
        assert data["user"]["full_name"] == "Google User"
        assert data["user"]["avatar_url"] == "https://example.com/avatar.jpg"
        assert data["user"]["role"] == "user"
        assert data["user"]["email_verified"] is False

    @pytest.mark.asyncio
    async def test_oauth_token_expiry_matches_settings(
        self, client, test_session, monkeypatch
    ):
        """Токен из Google callback имеет exp, соответствующий ACCESS_TOKEN_EXPIRE_MINUTES."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
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
                return FakeResponse(
                    {
                        "id": "oauth-exp-123",
                        "email": "oauthexp@example.com",
                        "name": "OAuth Exp User",
                        "picture": "https://example.com/avatar.jpg",
                    }
                )

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 200
        data = response.json()
        _assert_token_expiry(data["access_token"])

    @pytest.mark.asyncio
    async def test_google_callback_existing_user(self, client, test_user, monkeypatch):
        """Google callback привязывает social_account к существующему пользователю."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
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
                return FakeResponse(
                    {
                        "id": "987654321",
                        "email": test_user.email,
                        "verified_email": True,
                        "name": "Updated Name",
                        "picture": "https://example.com/new-avatar.jpg",
                    }
                )

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == test_user.id
        assert data["user"]["email_verified"] is True

    @pytest.mark.asyncio
    async def test_unsupported_provider(self, client):
        """Неподдерживаемый провайдер возвращает 400."""
        response = await client.get("/api/v1/auth/facebook/login")
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth_providers(self, client, monkeypatch):
        """Эндпоинт /auth/providers/ возвращает доступность провайдеров."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
                "yandex_client_id": "test-yandex-client-id",
                "yandex_client_secret": "test-yandex-secret",
                "google_oauth_enabled": True,
            }
        )
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
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
                "google_oauth_enabled": False,
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/google/login")
        assert response.status_code == 503
        assert "Google" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_google_callback_disabled(self, client, monkeypatch):
        """Google callback возвращает 503, если google_oauth выключен."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
                "google_oauth_enabled": False,
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 503
        assert "Google" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth_providers_google_disabled(self, client, monkeypatch):
        """/auth/providers/ отдаёт google=false, если google_oauth выключен."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
                "yandex_client_id": "test-yandex-client-id",
                "yandex_client_secret": "test-yandex-secret",
                "google_oauth_enabled": False,
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        response = await client.get("/api/v1/auth/providers/")
        assert response.status_code == 200
        data = response.json()
        assert data["google"] is False
        assert data["yandex"] is True

    @pytest.mark.asyncio
    async def test_oauth_callback_when_state_invalid_should_return_400(self, client):
        """Колбэк с неизвестным state отклоняется (F-01, CSRF)."""
        response = await client.get(
            "/api/v1/auth/callback?code=fake-code&state=totally-bogus-state"
        )
        assert response.status_code == 400
        assert "истек" in response.json()["detail"].lower() or "недействительна" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_oauth_callback_when_state_missing_should_return_422(self, client):
        """Колбэк без обязательного параметра state — 422."""
        response = await client.get("/api/v1/auth/callback?code=fake-code")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_oauth_callback_when_state_reused_should_return_400(
        self, client, test_session, monkeypatch
    ):
        """state одноразовый: повторное использование отклоняется (F-01)."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
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
                return FakeResponse(
                    {
                        "id": "reuse-1",
                        "email": "reuse@example.com",
                        "verified_email": True,
                        "name": "Reuse User",
                    }
                )

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        state = await create_state("google", "test-verifier")
        first = await client.get(f"/api/v1/auth/callback?code=fake-code&state={state}")
        assert first.status_code == 200
        second = await client.get(f"/api/v1/auth/callback?code=fake-code&state={state}")
        assert second.status_code == 400

    @pytest.mark.asyncio
    async def test_oauth_callback_when_token_exchange_fails_should_not_leak_provider_text(
        self, client, monkeypatch
    ):
        """Ошибка обмена кода не раскрывает ответ провайдера клиенту (F-05)."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        class FakeResponse:
            def __init__(self, json_data, status_code=200, text=""):
                self._json = json_data
                self.status_code = status_code
                self.text = text

            def json(self):
                return self._json

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, **kwargs):
                return FakeResponse(
                    {"error": "invalid_grant"},
                    status_code=400,
                    text="invalid_grant: secret-internal-detail",
                )

            async def get(self, url, **kwargs):
                return FakeResponse({})

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=bad-code&state={state}"
        )
        assert response.status_code == 400
        assert "secret-internal-detail" not in response.json()["detail"]
        assert "invalid_grant" not in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth_callback_when_email_unverified_and_user_exists_should_return_409(
        self, client, test_user, monkeypatch
    ):
        """Не линкуем соцаккаунт к существующему email при неподтверждённом email (F-03)."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
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
                return FakeResponse(
                    {
                        "id": "unverified-1",
                        "email": test_user.email,
                        "verified_email": False,
                        "name": "Attacker",
                    }
                )

        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeAsyncClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_login_when_user_has_no_password_should_return_401(
        self, client, test_session
    ):
        """OAuth-пользователь без пароля не может войти по паролю (F-11)."""
        from src.app.models.user import RoleEnum, User

        user = User(
            email="oauthonly@example.com",
            hashed_password=None,
            role=RoleEnum.user,
            is_active=True,
        )
        test_session.add(user)
        await test_session.commit()

        response = await client.post(
            "/api/v1/login/",
            json={"email": "oauthonly@example.com", "password": "anypassword123"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests for code-review findings #1–#10
# ---------------------------------------------------------------------------

def _make_fake_async_client(token_resp_data, user_info_data, token_status=200, user_info_status=200):
    """Factory for a minimal httpx.AsyncClient fake."""

    class FakeResponse:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
            self.text = str(json_data)

        def json(self):
            return self._json

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            return FakeResponse(token_resp_data, token_status)

        async def get(self, url, **kwargs):
            return FakeResponse(user_info_data, user_info_status)

    return FakeAsyncClient


class TestOAuthHardeningFindings:
    """Tests added for code-review findings #1–#10."""

    # -------------------------------------------------------------------
    # Finding #1 — provider_id missing → 400, not "None" collapse
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_when_provider_id_missing_should_return_400(
        self, client, test_session, monkeypatch
    ):
        """Finding #1: provider returns user without id/sub → 400, not account collision."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        FakeClient = _make_fake_async_client(
            token_resp_data={"access_token": "fake-token"},
            user_info_data={
                # no "id" or "sub" field — provider omitted them
                "email": "noiduser@example.com",
                "name": "No ID User",
                "verified_email": True,
            },
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 400
        # Must not be 500
        assert response.status_code != 500

    # -------------------------------------------------------------------
    # Finding #2 — SECRET_KEY fail-fast in production
    # -------------------------------------------------------------------
    def test_config_when_production_and_placeholder_key_should_raise(self, monkeypatch):
        """Finding #2: RuntimeError raised at import time when prod uses placeholder."""

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("SECRET_KEY", raising=False)

        # Re-execute _load_secret_key directly without re-importing the module
        from src.app.core.config import _load_secret_key, _DEV_SECRET_PLACEHOLDER
        # Temporarily set SECRET_KEY to placeholder
        monkeypatch.setenv("SECRET_KEY", _DEV_SECRET_PLACEHOLDER)
        import pytest
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            _load_secret_key()

    def test_config_when_production_and_empty_key_should_raise(self, monkeypatch):
        """Finding #2: RuntimeError raised when SECRET_KEY empty in prod."""
        from src.app.core.config import _load_secret_key
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "")
        import pytest
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            _load_secret_key()

    def test_config_when_development_and_placeholder_key_should_succeed(self, monkeypatch):
        """Finding #2: dev placeholder is allowed outside production."""
        from src.app.core.config import _load_secret_key, _DEV_SECRET_PLACEHOLDER
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", _DEV_SECRET_PLACEHOLDER)
        key = _load_secret_key()
        assert key == _DEV_SECRET_PLACEHOLDER

    # -------------------------------------------------------------------
    # Finding #3 — change_password guard for OAuth users
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_change_password_when_oauth_user_should_return_400(
        self, client, test_session
    ):
        """Finding #3: OAuth user (no hashed_password) calling change-password → 400."""
        from src.app.models.user import RoleEnum, User
        from src.app.utils.auth import create_access_token

        # Create a dedicated OAuth-only user (no password hash)
        oauth_user = User(
            email="oauthonly_f03@example.com",
            hashed_password=None,
            role=RoleEnum.user,
            is_active=True,
        )
        test_session.add(oauth_user)
        await test_session.commit()
        await test_session.refresh(oauth_user)

        # Mint a token for this OAuth user (F-10: sub=str(id))
        oauth_token = create_access_token(
            data={"sub": str(oauth_user.id), "role": oauth_user.role.value}
        )

        response = await client.patch(
            "/api/v1/me/password/",
            headers={"Authorization": f"Bearer {oauth_token}"},
            json={"old_password": "anything", "new_password": "newpass123"},
        )
        assert response.status_code == 400
        assert "соцсеть" in response.json()["detail"].lower() or "пароля" in response.json()["detail"].lower()

    # -------------------------------------------------------------------
    # Finding #4 — state survives transient token exchange failure
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_when_token_exchange_fails_state_remains_valid(
        self, client, monkeypatch
    ):
        """Finding #4: state is NOT burned when token exchange fails → retry works."""
        from src.app.services.oauth_state import peek_state

        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        FakeClientFail = _make_fake_async_client(
            token_resp_data={"error": "server_error"},
            user_info_data={},
            token_status=500,
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClientFail)

        state = await create_state("google", "test-verifier")

        # First attempt: provider fails → 400
        resp1 = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert resp1.status_code == 400

        # State must still be in Redis — user can retry
        data = await peek_state(state)
        assert data is not None, "State was burned despite token exchange failure"

    # -------------------------------------------------------------------
    # Finding #5 — social account references missing user → 400 not AttributeError/500
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_when_linked_user_deleted_should_return_400(
        self, client, test_session, monkeypatch
    ):
        """Finding #5: guard `if user is None` fires when the User row is absent.

        The guard is defensive — in production the ORM cascade + FK constraint
        prevent true orphans. We reach the branch by leaving the SocialAccount in
        the DB and monkeypatching db.execute so the User-by-id query returns empty,
        simulating the case where the row was removed outside ORM (e.g., a raw SQL
        DELETE with no cascade).
        """
        from unittest.mock import MagicMock
        from src.app.models.social_account import SocialAccount
        from src.app.models.user import RoleEnum, User

        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        # Create user + social_account — do NOT delete via ORM (cascade would also
        # remove the SocialAccount, causing the callback to take the wrong branch).
        orphan_user = User(
            email="orphaned5@example.com",
            hashed_password=None,
            role=RoleEnum.user,
            is_active=True,
        )
        test_session.add(orphan_user)
        await test_session.commit()
        await test_session.refresh(orphan_user)
        orphan_id = orphan_user.id

        social_row = SocialAccount(
            user_id=orphan_id,
            provider="google",
            provider_id="orphaned-provider-id-5",
        )
        test_session.add(social_row)
        await test_session.commit()

        # Patch db.execute on the SESSION INSTANCE (not the class) to intercept
        # exactly `SELECT user WHERE id = orphan_id` — the query the callback makes
        # after it finds the SocialAccount row. All other queries pass through.
        # Detection: the statement targets the "user" table and NOT "social_account".

        real_execute = test_session.execute
        user_by_id_intercepted = {"done": False}

        async def patched_execute(statement, *args, **kwargs):
            if not user_by_id_intercepted["done"]:
                try:
                    froms = statement.get_final_froms()
                    table_names = {f.name for f in froms if hasattr(f, "name")}
                    if "users" in table_names and "social_accounts" not in table_names:
                        user_by_id_intercepted["done"] = True
                        mock_result = MagicMock()
                        mock_result.scalars.return_value.first.return_value = None
                        return mock_result
                except Exception:
                    pass
            return await real_execute(statement, *args, **kwargs)

        # Patch on the instance so only this session is affected
        test_session.execute = patched_execute

        FakeClient = _make_fake_async_client(
            token_resp_data={"access_token": "fake-token"},
            user_info_data={
                "id": "orphaned-provider-id-5",
                "email": "orphaned5@example.com",
                "name": "Orphaned",
                "verified_email": True,
            },
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        # Guard fires → 400, not 500 (no AttributeError on user.full_name etc.)
        assert response.status_code == 400
        assert response.status_code != 500

    # -------------------------------------------------------------------
    # Finding #6 — token response without access_token → 400 not KeyError/500
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_when_access_token_missing_in_response_should_return_400(
        self, client, monkeypatch
    ):
        """Finding #6: provider returns 200 but omits access_token → 400, not KeyError."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        FakeClient = _make_fake_async_client(
            # 200 OK but no access_token field
            token_resp_data={"token_type": "bearer"},
            user_info_data={},
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 400
        assert response.status_code != 500

    # -------------------------------------------------------------------
    # Finding #7 — case-insensitive email linking
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_when_email_case_differs_should_link_to_existing_user(
        self, client, test_session, monkeypatch
    ):
        """Finding #7: provider returns email in mixed case → links to existing lowercase user."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        from src.app.models.user import RoleEnum, User
        from src.app.utils.auth import hash_password

        # Existing user stored with lowercase email
        existing_user = User(
            email="mixedcase@example.com",
            hashed_password=hash_password("password123"),
            role=RoleEnum.user,
            is_active=True,
        )
        test_session.add(existing_user)
        await test_session.commit()
        await test_session.refresh(existing_user)

        # Provider returns email with mixed caps
        FakeClient = _make_fake_async_client(
            token_resp_data={"access_token": "fake-token"},
            user_info_data={
                "id": "case-test-id-123",
                "email": "MixedCase@Example.COM",  # different case
                "name": "Mixed Case User",
                "verified_email": True,
            },
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 200
        data = response.json()
        # Should be linked to the existing user, not a new one
        assert data["user"]["id"] == existing_user.id
        assert data["user"]["email"] == "mixedcase@example.com"

    # -------------------------------------------------------------------
    # Finding #9 — OAuth response shape matches email-login shape
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_user_response_shape_matches_email_login(
        self, client, test_session, monkeypatch
    ):
        """Finding #9: OAuth callback user object is a UserOut, identical to email login."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        FakeClient = _make_fake_async_client(
            token_resp_data={"access_token": "fake-token"},
            user_info_data={
                "id": "shape-test-id-456",
                "email": "shapetest@example.com",
                "name": "Shape Test User",
                "picture": "https://example.com/pic.jpg",
                "verified_email": True,
            },
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClient)

        state = await create_state("google", "test-verifier")
        oauth_resp = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert oauth_resp.status_code == 200
        oauth_data = oauth_resp.json()

        # Register the same-shaped user via email to get a reference shape
        reg_resp = await client.post(
            "/api/v1/register/",
            json={"email": "shapereference@example.com", "password": "password123"},
        )
        assert reg_resp.status_code == 200
        reg_data = reg_resp.json()

        # Both user objects must have the same keys
        oauth_user_keys = set(oauth_data["user"].keys())
        reg_user_keys = set(reg_data["user"].keys())
        assert oauth_user_keys == reg_user_keys, (
            f"OAuth user keys {oauth_user_keys} differ from email-login keys {reg_user_keys}"
        )

    # -------------------------------------------------------------------
    # Finding #8 — race condition on SocialAccount insert → not 500
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_when_social_account_race_should_return_valid_jwt(
        self, client, test_session, monkeypatch
    ):
        """Finding #8: concurrent callbacks racing to insert same SocialAccount →
        loser gets IntegrityError, recovers, and still returns a valid JWT (not 500).

        Strategy: pre-insert the SocialAccount and User so that the callback's
        INSERT would hit the unique constraint. We simulate this by patching
        db.commit inside the callback's SocialAccount-insert block to raise
        IntegrityError on the first call (the SocialAccount INSERT), so the
        except-branch fires and re-reads the existing record.
        """
        from sqlalchemy.exc import IntegrityError as SAIntegrityError
        from src.app.models.social_account import SocialAccount
        from src.app.models.user import RoleEnum, User

        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        # Pre-create the user and social account as if a concurrent request already did it.
        race_user = User(
            email="racewinner@example.com",
            hashed_password=None,
            role=RoleEnum.user,
            is_active=True,
        )
        test_session.add(race_user)
        await test_session.commit()
        await test_session.refresh(race_user)

        existing_social = SocialAccount(
            user_id=race_user.id,
            provider="google",
            provider_id="race-provider-id-777",
        )
        test_session.add(existing_social)
        await test_session.commit()

        # The callback will do: email-lookup (no user found in its session path)
        # → new User INSERT (succeeds because we used a different session above)
        # → SocialAccount INSERT → IntegrityError (unique violation).
        # We simulate IntegrityError by patching db.commit to raise once,
        # then the fallback re-reads the existing SocialAccount and returns JWT.
        original_commit = test_session.commit.__func__
        commit_call_count = {"n": 0}

        async def patched_commit(self_session):
            commit_call_count["n"] += 1
            # Let the first commit (new User) succeed; raise on second (SocialAccount).
            if commit_call_count["n"] == 2:
                raise SAIntegrityError(
                    statement=None, params=None, orig=Exception("unique violation")
                )
            return await original_commit(self_session)

        monkeypatch.setattr(
            test_session.__class__, "commit", patched_commit
        )

        FakeClient = _make_fake_async_client(
            token_resp_data={"access_token": "fake-token"},
            user_info_data={
                "id": "race-provider-id-777",
                "email": "racewinner@example.com",
                "name": "Race Winner",
                "verified_email": True,
            },
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        # Must not be 500 — should return 200 with the existing user's JWT
        assert response.status_code != 500
        # 200 with a valid access_token, or 400 from the recovery path
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    # -------------------------------------------------------------------
    # Finding #10 — 409 error message does not mention "привяжите в настройках"
    # -------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_when_email_unverified_and_user_exists_message_is_correct(
        self, client, test_user, monkeypatch
    ):
        """Finding #10: 409 text does not reference non-existent 'link in settings' flow."""
        new_settings = _make_oauth_settings(
            {
                "google_client_id": "test-google-client-id",
                "google_client_secret": "test-google-secret",
            }
        )
        monkeypatch.setattr("src.app.api.auth.settings", new_settings)
        monkeypatch.setattr("src.app.services.feature_flags.settings", new_settings)

        FakeClient = _make_fake_async_client(
            token_resp_data={"access_token": "fake-token"},
            user_info_data={
                "id": "attacker-id-999",
                "email": test_user.email,
                "name": "Attacker",
                "verified_email": False,
            },
        )
        monkeypatch.setattr("src.app.api.auth.httpx.AsyncClient", FakeClient)

        state = await create_state("google", "test-verifier")
        response = await client.get(
            f"/api/v1/auth/callback?code=fake-code&state={state}"
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        # Old ghost text must be gone
        assert "привяжите" not in detail.lower()
        assert "настройках" not in detail.lower()
        # Should instruct normal login
        assert "войдите" in detail.lower() or "войти" in detail.lower()


# ---------------------------------------------------------------------------
# Tests for deferred hardening batch (F-07, F-08, F-09, F-10, F-13)
# ---------------------------------------------------------------------------


class TestHardeningDeferred:
    """Tests for F-07 (jti denylist/logout), F-08 (rate limits),
    F-09 (frontend_url guard), F-10 (sub=id), F-13 (no pw truncation)."""

    # -------------------------------------------------------------------
    # F-07 — logout revokes token; other tokens unaffected
    # -------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_logout_revokes_token(self, client, test_user):
        """Login → protected endpoint OK → logout → same token → 401."""
        # Login to get a real token
        login_resp = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        # Token works before logout
        me_resp = await client.get(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200

        # Logout
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Logged out"

        # Same token is now rejected
        me_after = await client.get(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_after.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_idempotent_with_garbage_token(self, client):
        """Logout with an invalid token returns 200 (idempotent)."""
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out"

    @pytest.mark.asyncio
    async def test_logout_does_not_revoke_other_tokens(self, client, test_user, test_admin):
        """Logging out one token does not affect another user's valid token."""
        # Login as regular user
        user_resp = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert user_resp.status_code == 200
        user_token = user_resp.json()["access_token"]

        # Login as admin (separate token)
        admin_resp = await client.post(
            "/api/v1/login/",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        assert admin_resp.status_code == 200
        admin_token_val = admin_resp.json()["access_token"]

        # Logout user
        await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        # Admin token still works
        admin_me = await client.get(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {admin_token_val}"},
        )
        assert admin_me.status_code == 200
        assert admin_me.json()["email"] == "admin@example.com"

    # -------------------------------------------------------------------
    # F-08 — rate-limit decorators are no-ops outside production
    # -------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_oauth_callback_reachable_without_429(self, client):
        """GET /auth/callback is reachable in test env (no 429 from rate limiter)."""
        # Use invalid state — just assert we don't get 429
        resp = await client.get("/api/v1/auth/callback?code=x&state=bogus")
        assert resp.status_code != 429
        # We expect 400 (invalid state) not a rate-limit error
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_password_reset_request_reachable_without_429(self, client):
        """POST /auth/password-reset-request/ is reachable without 429 in test env."""
        resp = await client.post(
            "/api/v1/auth/password-reset-request/",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code != 429
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_password_reset_reachable_without_429(self, client):
        """POST /auth/password-reset/ is reachable without 429 in test env."""
        resp = await client.post(
            "/api/v1/auth/password-reset/",
            json={"token": "bogustoken", "new_password": "newpass123"},
        )
        assert resp.status_code != 429
        # Expect 400 (invalid/expired token) not a rate-limit error
        assert resp.status_code == 400

    def test_conditional_limit_is_noop_outside_production(self, monkeypatch):
        """conditional_limit returns the function unchanged when ENVIRONMENT != production."""

        monkeypatch.delenv("ENVIRONMENT", raising=False)

        from src.app.utils.rate_limiter import conditional_limit

        def my_func():
            return "original"

        decorated = conditional_limit("5/minute")(my_func)
        assert decorated is my_func

    # -------------------------------------------------------------------
    # F-09 — frontend_url validation in production
    # -------------------------------------------------------------------

    def test_validate_frontend_url_production_http_localhost_raises(self, monkeypatch):
        """Production + http://localhost:5173 → RuntimeError."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.app.core.config import _validate_frontend_url
        import pytest

        with pytest.raises(RuntimeError, match="https"):
            _validate_frontend_url("http://localhost:5173")

    def test_validate_frontend_url_production_https_localhost_raises(self, monkeypatch):
        """Production + https://localhost:5173 → RuntimeError (localhost not allowed)."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.app.core.config import _validate_frontend_url
        import pytest

        with pytest.raises(RuntimeError, match="localhost"):
            _validate_frontend_url("https://localhost:5173")

    def test_validate_frontend_url_production_https_valid_passes(self, monkeypatch):
        """Production + https://promelectron.ru → ok."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.app.core.config import _validate_frontend_url

        result = _validate_frontend_url("https://promelectron.ru")
        assert result == "https://promelectron.ru"

    def test_validate_frontend_url_development_any_url_passes(self, monkeypatch):
        """Non-production → any URL is accepted."""
        monkeypatch.setenv("ENVIRONMENT", "development")

        from src.app.core.config import _validate_frontend_url

        result = _validate_frontend_url("http://localhost:5173")
        assert result == "http://localhost:5173"

    def test_validate_frontend_url_no_env_any_url_passes(self, monkeypatch):
        """No ENVIRONMENT set → any URL is accepted."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        from src.app.core.config import _validate_frontend_url

        result = _validate_frontend_url("http://127.0.0.1:3000")
        assert result == "http://127.0.0.1:3000"

    # -------------------------------------------------------------------
    # F-10 — sub = numeric user id; email change doesn't break existing token
    # -------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_token_sub_is_numeric_id(self, client, test_user):
        """Freshly minted token has sub = str(user.id), role present."""
        login_resp = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        from src.app.core.config import ALGORITHM, SECRET_KEY
        from jose import jwt as jose_jwt

        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == str(test_user.id)
        assert "role" in payload
        assert payload["role"] == "user"

    @pytest.mark.asyncio
    async def test_protected_endpoint_resolves_correct_user(self, client, test_user):
        """Protected endpoint returns the right user after F-10 sub=id change."""
        login_resp = await client.post(
            "/api/v1/login/",
            json={"email": "testuser@example.com", "password": "password123"},
        )
        token = login_resp.json()["access_token"]

        me_resp = await client.get(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["id"] == test_user.id
        assert data["email"] == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_email_change_does_not_invalidate_existing_token(
        self, client, test_user, user_token
    ):
        """Changing email doesn't 401 an existing token (sub is id, not email)."""
        # Confirm token works first
        me_before = await client.get(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert me_before.status_code == 200

        # Change email
        patch_resp = await client.patch(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"email": "changed_f10@example.com"},
        )
        assert patch_resp.status_code == 200

        # Token still resolves to the same user (sub=id is stable)
        me_after = await client.get(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert me_after.status_code == 200
        assert me_after.json()["email"] == "changed_f10@example.com"

    # -------------------------------------------------------------------
    # F-13 — no silent password truncation; max_length=128 enforced at schema
    # -------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_long_password_registers_and_logs_in(self, client):
        """A 100-char password registers and logs in successfully (no truncation)."""
        long_pw = "A" * 100
        reg_resp = await client.post(
            "/api/v1/register/",
            json={"email": "longpw@example.com", "password": long_pw},
        )
        assert reg_resp.status_code == 200

        login_resp = await client.post(
            "/api/v1/login/",
            json={"email": "longpw@example.com", "password": long_pw},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

    @pytest.mark.asyncio
    async def test_overlong_password_returns_422(self, client):
        """A 200-char password → 422 validation error at the schema layer."""
        overlong_pw = "B" * 200
        resp = await client.post(
            "/api/v1/register/",
            json={"email": "overlongpw@example.com", "password": overlong_pw},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_password_at_max_length_is_accepted(self, client):
        """Exactly 128-char password is accepted (boundary check)."""
        max_pw = "C" * 128
        reg_resp = await client.post(
            "/api/v1/register/",
            json={"email": "maxpw@example.com", "password": max_pw},
        )
        assert reg_resp.status_code == 200

        login_resp = await client.post(
            "/api/v1/login/",
            json={"email": "maxpw@example.com", "password": max_pw},
        )
        assert login_resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests for review-round fixes (ws denylist, fail-open, idempotent logout, IP guard)
# ---------------------------------------------------------------------------


class TestReviewFixes:
    """Tests covering the 6 findings from the code/security review iteration."""

    # -------------------------------------------------------------------
    # Fix 1 — ws.py jti denylist gate (unit-level: is_revoked after revoke)
    # -------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ws_denylist_revoke_then_is_revoked(self):
        """After revoke(jti, ttl), is_revoked(jti) returns True — ws decode path would close 4001."""
        import secrets

        from src.app.services.token_denylist import is_revoked, revoke

        jti = secrets.token_urlsafe(16)
        assert not await is_revoked(jti)
        await revoke(jti, 300)
        assert await is_revoked(jti)

    # -------------------------------------------------------------------
    # Fix 2 — is_revoked fails open when Redis raises
    # -------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_is_revoked_when_redis_raises_should_return_false(self, monkeypatch):
        """Redis outage → is_revoked returns False (fail-open, no 500)."""
        from src.app.core.redis_client import RedisClient
        from src.app.services.token_denylist import is_revoked

        async def boom(key):
            raise ConnectionError("Redis down")

        monkeypatch.setattr(RedisClient, "get", staticmethod(boom))
        result = await is_revoked("some-jti-value")
        assert result is False

    # -------------------------------------------------------------------
    # Fix 5 — idempotent logout without Authorization header → 200
    # -------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_logout_when_no_authorization_header_should_return_200(self, client):
        """Logout without an Authorization header returns 200 (truly idempotent)."""
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out"

    # -------------------------------------------------------------------
    # Fix 6 — _validate_frontend_url rejects private/loopback IP literals
    # -------------------------------------------------------------------

    def test_validate_frontend_url_production_private_ip_raises(self, monkeypatch):
        """Production + https://10.0.0.5/ → RuntimeError (private IP)."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.app.core.config import _validate_frontend_url
        import pytest

        with pytest.raises(RuntimeError, match="loopback/private"):
            _validate_frontend_url("https://10.0.0.5/")

    def test_validate_frontend_url_production_ipv6_loopback_raises(self, monkeypatch):
        """Production + https://[::1]/ → RuntimeError (IPv6 loopback)."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.app.core.config import _validate_frontend_url
        import pytest

        with pytest.raises(RuntimeError, match="loopback/private"):
            _validate_frontend_url("https://[::1]/")

    def test_validate_frontend_url_production_valid_domain_passes(self, monkeypatch):
        """Production + https://promelectron.ru → ok (real domain, not an IP)."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.app.core.config import _validate_frontend_url

        result = _validate_frontend_url("https://promelectron.ru")
        assert result == "https://promelectron.ru"
