import pytest
from sqlalchemy import select

from src.app.models.user import PasswordResetToken
from src.app.utils.auth import verify_password


class TestPasswordResetAPI:
    """Тесты сброса пароля."""

    @pytest.mark.asyncio
    async def test_password_reset_request_creates_token(self, client, test_user, test_session):
        """Запрос сброса пароля создаёт токен в БД."""
        response = await client.post(
            "/api/v1/auth/password-reset-request/",
            json={"email": test_user.email},
        )
        assert response.status_code == 200
        assert "message" in response.json()

        result = await test_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == test_user.id)
        )
        token = result.scalars().first()
        assert token is not None
        assert token.used_at is None
        assert not token.is_expired()

    @pytest.mark.asyncio
    async def test_password_reset_request_nonexistent_email(self, client):
        """Запрос для несуществующего email возвращает успешный ответ."""
        response = await client.post(
            "/api/v1/auth/password-reset-request/",
            json={"email": "missing@example.com"},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_password_reset_request_invalid_email(self, client):
        """Невалидный email отклоняется."""
        response = await client.post(
            "/api/v1/auth/password-reset-request/",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_password_reset_changes_password(self, client, test_user, test_session):
        """Сброс пароля по токену меняет пароль пользователя."""
        from src.app.services.user_service import UserService

        token = await UserService.create_password_reset_token(user_id=test_user.id, db=test_session)

        response = await client.post(
            "/api/v1/auth/password-reset/",
            json={"token": token, "new_password": "newpass123"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password reset successfully"

        await test_session.refresh(test_user)
        assert verify_password("newpass123", test_user.hashed_password)

        # Токен помечен как использованный
        result = await test_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == test_user.id)
        )
        reset_token = result.scalars().first()
        assert reset_token.used_at is not None

    @pytest.mark.asyncio
    async def test_password_reset_invalid_token(self, client):
        """Неверный токен отклоняется."""
        response = await client.post(
            "/api/v1/auth/password-reset/",
            json={"token": "invalid-token", "new_password": "newpass123"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_password_reset_short_password(self, client):
        """Слишком короткий пароль отклоняется."""
        response = await client.post(
            "/api/v1/auth/password-reset/",
            json={"token": "some-token", "new_password": "123"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_password_reset_expired_token(self, client, test_user, test_session):
        """Истёкший токен отклоняется."""
        from datetime import datetime, timedelta, timezone

        from src.app.services.user_service import UserService

        token = await UserService.create_password_reset_token(user_id=test_user.id, db=test_session)

        # Истекаем токен вручную
        result = await test_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == test_user.id)
        )
        reset_token = result.scalars().first()
        reset_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()

        response = await client.post(
            "/api/v1/auth/password-reset/",
            json={"token": token, "new_password": "newpass123"},
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
