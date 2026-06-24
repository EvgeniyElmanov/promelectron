from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from urllib.parse import urlencode

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.models.social_account import SocialAccount
from src.app.schemas.user import PasswordResetConfirm, PasswordResetRequest, UserOut
from src.app.core.config import settings
from src.app.services.feature_flags import is_enabled
from src.app.services.user_service import UserService
from src.app.utils.auth import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
        # prompt=select_account заставляет Google показывать выбор аккаунта
        # при каждом входе, даже если в браузере одна активная сессия.
        "extra_auth_params": {"prompt": "select_account"},
    },
    "yandex": {
        "auth_url": "https://oauth.yandex.ru/authorize",
        "token_url": "https://oauth.yandex.ru/token",
        "user_info_url": "https://login.yandex.ru/info?format=json",
        "scope": "login:email login:info",
        # force_confirm=yes заставляет Яндекс показывать экран подтверждения
        # и выбора аккаунта при каждом входе, а не молча переиспользовать
        # ранее выданное разрешение (issue #4).
        "extra_auth_params": {"force_confirm": "yes"},
    },
}


def get_provider_config(provider: str) -> dict:
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    return OAUTH_PROVIDERS[provider]


async def get_provider_credentials(provider: str) -> tuple[str, str]:
    if provider == "google":
        if not await is_enabled("google_oauth", default=True):
            raise HTTPException(
                status_code=503,
                detail="Вход через Google временно недоступен. Попробуйте позже или используйте email.",
            )
        if not settings.google_client_id or not settings.google_client_secret:
            raise HTTPException(
                status_code=503,
                detail="Вход через Google не настроен. Попробуйте позже или используйте email.",
            )
        return settings.google_client_id, settings.google_client_secret
    elif provider == "yandex":
        if not settings.yandex_client_id or not settings.yandex_client_secret:
            raise HTTPException(
                status_code=503,
                detail="Вход через Яндекс временно недоступен. Попробуйте позже или используйте email.",
            )
        return settings.yandex_client_id, settings.yandex_client_secret
    raise HTTPException(status_code=400, detail="Unsupported provider")


@router.get("/profile", response_model=UserOut)
async def get_auth_profile(
    current_user: User = Depends(get_current_user),
):
    """Получить профиль текущего пользователя."""
    return current_user


@router.get("/providers/")
async def oauth_providers():
    """Вернуть доступность OAuth-провайдеров для текущего окружения."""
    return {
        "google": await is_enabled("google_oauth", default=True)
        and bool(settings.google_client_id),
        "yandex": bool(settings.yandex_client_id),
    }


@router.get("/{provider}/login")
async def oauth_login(provider: str):
    config = get_provider_config(provider)
    client_id, _ = await get_provider_credentials(provider)
    redirect_uri = f"{settings.frontend_url}/auth/callback"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": config["scope"],
        "state": provider,
        **config.get("extra_auth_params", {}),
    }

    auth_url = f"{config['auth_url']}?{urlencode(auth_params)}"

    return {"url": auth_url}


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    config = get_provider_config(provider)
    client_id, client_secret = await get_provider_credentials(provider)
    redirect_uri = f"{settings.frontend_url}/auth/callback"

    # 1. Обмен кода на токен
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            config["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to get token: {token_resp.text}")
        token_data = token_resp.json()

    # 2. Получение данных пользователя
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            config["user_info_url"],
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to get user info: {user_resp.text}")
        user_info = user_resp.json()

    email = user_info.get("email") or user_info.get("default_email")
    provider_id = str(user_info.get("id") or user_info.get("sub"))

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by provider")

    # 3. Поиск или создание пользователя
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    # Извлекаем доп. данные из профиля провайдера
    full_name = user_info.get("name") or user_info.get("real_name") or user_info.get("display_name")
    avatar_url = user_info.get("picture") or user_info.get("default_avatar_id")
    if avatar_url and provider == "yandex" and not avatar_url.startswith("http"):
        avatar_url = f"https://avatars.yandex.net/get-yapic/{avatar_url}/islands-200"

    if not user:
        user = User(
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            hashed_password="",  # OAuth-пользователь без пароля
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Обновляем профиль если данные пустые
        updated = False
        if full_name and not user.full_name:
            user.full_name = full_name
            updated = True
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            updated = True
        if updated:
            await db.commit()
            await db.refresh(user)

    # 4. Привязка соц. аккаунта
    social_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.provider == provider,
            SocialAccount.provider_id == provider_id,
        )
    )
    social = social_result.scalars().first()

    if not social:
        social = SocialAccount(
            user_id=user.id,
            provider=provider,
            provider_id=provider_id,
            access_token=token_data.get("access_token"),
        )
        db.add(social)
        await db.commit()
    else:
        # Обновляем токен если изменился
        if social.access_token != token_data.get("access_token"):
            social.access_token = token_data.get("access_token")
            await db.commit()

    # 5. Генерация JWT
    jwt_token = create_access_token(data={"sub": user.email, "role": user.role.value})

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "role": user.role.value,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/password-reset-request/")
async def password_reset_request(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Запросить ссылку на сброс пароля.

    Всегда возвращает успешный ответ, чтобы не раскрывать существование email.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if user:
        token = await UserService.create_password_reset_token(user_id=user.id, db=db)
        # Email отправляется в best-effort режиме; без SMTP просто логируем
        from src.app.services.email_service import EmailService

        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
        try:
            await EmailService.send_email(
                to=user.email,
                subject="MyShop — Сброс пароля",
                html=f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #181818;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <h2 style="color: #005BFF;">MyShop — Сброс пароля</h2>
    <p>Для сброса пароля перейдите по ссылке:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p style="color: #6c757d; font-size: 12px;">Ссылка действительна 24 часа.</p>
  </div>
</body>
</html>
""",
                text=f"Сброс пароля: {reset_url} (действует 24 часа).",
            )
        except Exception:
            pass

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/")
async def password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Сбросить пароль по одноразовому токену."""
    return await UserService.reset_password(
        token=data.token, new_password=data.new_password, db=db
    )
