import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from src.app.models.user import EmailVerificationToken, User
from src.app.services.email_service import EmailService
from src.app.services.user_service import UserService


class TestEmailVerificationAPI:
    """Тесты подтверждения email при регистрации."""

    @pytest.mark.asyncio
    async def test_registration_creates_verification_token(
        self, client, test_session
    ):
        """Регистрация создаёт EmailVerificationToken и отправляет письмо."""
        response = await client.post(
            "/api/v1/register/",
            json={"email": "verifyme@example.com", "password": "securepass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email_verified"] is False

        user_result = await test_session.execute(
            select(User).where(User.email == "verifyme@example.com")
        )
        user = user_result.scalars().first()
        assert user is not None

        token_result = await test_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id
            )
        )
        token = token_result.scalars().first()
        assert token is not None
        assert token.used_at is None
        assert token.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_verify_email_with_valid_token_redirects_to_success(
        self, client, test_session
    ):
        """Валидный токен подтверждает email и редиректит на success."""
        # Register a user to get a verification token
        reg_response = await client.post(
            "/api/v1/register/",
            json={"email": "verify@example.com", "password": "securepass123"},
        )
        assert reg_response.status_code == 200
        user_id = reg_response.json()["user"]["id"]

        token_result = await test_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id
            )
        )
        token_row = token_result.scalars().first()
        plaintext_token = await UserService.create_email_verification_token(
            user_id=user_id, db=test_session
        )

        # Mock email service to avoid actual sending in this test
        with patch.object(
            EmailService, "send_verification_email", new=AsyncMock()
        ):
            response = await client.get(
                f"/api/v1/auth/verify-email/?token={plaintext_token}"
            )

        assert response.status_code == 302
        location = response.headers.get("location")
        assert "/verify-email/success" in location

        await test_session.refresh(token_row)
        user_result = await test_session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalars().first()
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_with_invalid_token_redirects_to_error(
        self, client
    ):
        """Невалидный токен редиректит на страницу ошибки."""
        response = await client.get("/api/v1/auth/verify-email/?token=invalid-token")
        assert response.status_code == 302
        location = response.headers.get("location")
        assert "/verify-email/error" in location
        assert "reason=invalid" in location

    @pytest.mark.asyncio
    async def test_verify_email_with_expired_token_redirects_to_error(
        self, client, test_session
    ):
        """Истёкший токен редиректит на страницу ошибки."""
        reg_response = await client.post(
            "/api/v1/register/",
            json={"email": "expired@example.com", "password": "securepass123"},
        )
        assert reg_response.status_code == 200
        user_id = reg_response.json()["user"]["id"]

        # Create a token and expire it manually
        plaintext_token = await UserService.create_email_verification_token(
            user_id=user_id, db=test_session
        )
        token_hash = hashlib.sha256(plaintext_token.encode()).hexdigest()
        token_result = await test_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )
        token_row = token_result.scalars().first()
        token_row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await test_session.commit()

        response = await client.get(
            f"/api/v1/auth/verify-email/?token={plaintext_token}"
        )
        assert response.status_code == 302
        location = response.headers.get("location")
        assert "/verify-email/error" in location
        assert "reason=expired" in location

    @pytest.mark.asyncio
    async def test_verify_email_token_single_use(
        self, client, test_session
    ):
        """Токен одноразовый — повторное использование редиректит на ошибку."""
        reg_response = await client.post(
            "/api/v1/register/",
            json={"email": "singleuse@example.com", "password": "securepass123"},
        )
        assert reg_response.status_code == 200
        user_id = reg_response.json()["user"]["id"]

        plaintext_token = await UserService.create_email_verification_token(
            user_id=user_id, db=test_session
        )

        # First use succeeds
        first = await client.get(
            f"/api/v1/auth/verify-email/?token={plaintext_token}",
            follow_redirects=False,
        )
        assert first.status_code == 302
        assert "/verify-email/success" in first.headers["location"]

        # Second use fails
        second = await client.get(
            f"/api/v1/auth/verify-email/?token={plaintext_token}",
            follow_redirects=False,
        )
        assert second.status_code == 302
        assert "/verify-email/error" in second.headers["location"]

    @pytest.mark.asyncio
    async def test_resend_verification_invalidates_old_token(
        self, client, test_user, user_token, test_session
    ):
        """Повторная отправка инвалидирует старый токен и создаёт новый."""
        old_token = await UserService.create_email_verification_token(
            user_id=test_user.id, db=test_session
        )
        old_hash = hashlib.sha256(old_token.encode()).hexdigest()

        with patch.object(
            EmailService, "send_verification_email", new=AsyncMock()
        ):
            response = await client.post(
                "/api/v1/auth/resend-verification/",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )

        assert response.status_code == 200
        assert "instructions have been sent" in response.json()["message"]

        old_token_result = await test_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == old_hash
            )
        )
        old_token_row = old_token_result.scalar_one_or_none()
        assert old_token_row is not None
        assert old_token_row.used_at is not None

    @pytest.mark.asyncio
    async def test_resend_verification_unauthorized_requires_email(
        self, client, test_user, test_session
    ):
        """Неавторизованная повторная отправка работает по email."""
        with patch.object(
            EmailService, "send_verification_email", new=AsyncMock()
        ):
            response = await client.post(
                "/api/v1/auth/resend-verification/",
                json={"email": test_user.email},
            )

        assert response.status_code == 200
        assert "instructions have been sent" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_resend_verification_unauthorized_missing_email(
        self, client
    ):
        """Неавторизованная отправка без email возвращает успешный ответ."""
        response = await client.post(
            "/api/v1/auth/resend-verification/",
            json={},
        )
        assert response.status_code == 200
        assert "instructions have been sent" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_update_profile_email_resets_verified_flag(
        self, client, test_user, user_token, test_session
    ):
        """Смена email в профиле сбрасывает email_verified и инвалидирует токены."""
        # Pre-verify the user
        test_user.email_verified = True
        await test_session.commit()

        token = await UserService.create_email_verification_token(
            user_id=test_user.id, db=test_session
        )
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        response = await client.patch(
            "/api/v1/me/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"email": "newemail@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "newemail@example.com"
        assert response.json()["email_verified"] is False

        await test_session.refresh(test_user)
        assert test_user.email_verified is False

        token_result = await test_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )
        token_row = token_result.scalar_one_or_none()
        assert token_row is None or token_row.used_at is not None

    @pytest.mark.asyncio
    async def test_resend_verification_skips_already_verified(
        self, client, test_user, user_token, test_session
    ):
        """Повторная отправка для верифицированного пользователя не создаёт токен."""
        test_user.email_verified = True
        await test_session.commit()

        with patch.object(
            EmailService, "send_verification_email", new=AsyncMock()
        ) as mock_send:
            response = await client.post(
                "/api/v1/auth/resend-verification/",
                headers={"Authorization": f"Bearer {user_token}"},
                json={},
            )

        assert response.status_code == 200
        assert "instructions have been sent" in response.json()["message"]
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_resend_verification_rate_limit_blocks_second_request(
        self, test_user, test_session, monkeypatch
    ):
        """В production повторная отправка чаще 1 раза в минуту возвращает 429."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("CI", raising=False)

        import importlib
        from src.app.api import auth

        importlib.reload(auth)

        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded

        from src.app.db.database import get_db
        from src.app.utils.rate_limiter import limiter

        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.include_router(auth.router, prefix="/api/v1")

        async def override_get_db():
            yield test_session

        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            first = await ac.post(
                "/api/v1/auth/resend-verification/",
                json={"email": test_user.email},
            )
            assert first.status_code == 200

            second = await ac.post(
                "/api/v1/auth/resend-verification/",
                json={"email": test_user.email},
            )
            assert second.status_code == 429

    @pytest.mark.asyncio
    async def test_verify_email_rate_limit_blocks_request_over_limit(
        self, test_session, monkeypatch
    ):
        """В production verify-email чаще 5 раз в минуту возвращает 429."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("CI", raising=False)

        import importlib
        from src.app.api import auth

        # Use a fresh Limiter instance so this test is isolated from other
        # tests that share the global limiter singleton.
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        fresh_limiter = Limiter(key_func=get_remote_address)
        monkeypatch.setattr(
            "src.app.utils.rate_limiter.limiter", fresh_limiter
        )

        importlib.reload(auth)

        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded

        from src.app.db.database import get_db

        app = FastAPI()
        app.state.limiter = fresh_limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.include_router(auth.router, prefix="/api/v1")

        async def override_get_db():
            yield test_session

        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            for i in range(5):
                response = await ac.get(
                    f"/api/v1/auth/verify-email/?token=token-{i}"
                )
                assert response.status_code == 302

            over_limit = await ac.get("/api/v1/auth/verify-email/?token=token-limit")
            assert over_limit.status_code == 429


class TestEmailVerificationModel:
    """Unit-тесты модели EmailVerificationToken."""

    def test_email_verification_token_indexes(self):
        """F-015: Модель содержит требуемые индексы."""
        from src.app.models.user import EmailVerificationToken

        index_names = {
            idx.name for idx in EmailVerificationToken.__table_args__
            if hasattr(idx, "name")
        }
        assert "ix_email_verification_tokens_user_id_created_at" in index_names
        assert "ix_email_verification_tokens_expires_at" in index_names


class TestEmailVerificationService:
    """Unit-тесты сервиса подтверждения email."""

    @pytest.mark.asyncio
    async def test_create_email_verification_token_invalidates_old_tokens(
        self, test_user, test_session
    ):
        """Создание нового токена помечает старые как использованные."""
        first = await UserService.create_email_verification_token(
            user_id=test_user.id, db=test_session
        )
        first_hash = hashlib.sha256(first.encode()).hexdigest()

        second = await UserService.create_email_verification_token(
            user_id=test_user.id, db=test_session
        )

        first_result = await test_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == first_hash
            )
        )
        first_row = first_result.scalar_one()
        assert first_row.used_at is not None
        assert first_row.token_hash != hashlib.sha256(second.encode()).hexdigest()

    @pytest.mark.asyncio
    async def test_verify_email_token_sets_user_verified(
        self, test_user, test_session
    ):
        """verify_email_token выставляет email_verified=True."""
        plaintext_token = await UserService.create_email_verification_token(
            user_id=test_user.id, db=test_session
        )

        user = await UserService.verify_email_token(
            token=plaintext_token, db=test_session
        )
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_token_invalid_raises(self, test_session):
        """verify_email_token с невалидным токеном бросает 400."""
        with pytest.raises(HTTPException) as exc_info:
            await UserService.verify_email_token(
                token="totally-invalid", db=test_session
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid token"
