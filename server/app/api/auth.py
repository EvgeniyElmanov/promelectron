from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.models.social_account import SocialAccount
from server.app.schemas.user import UserOut
from server.app.core.config import settings
from server.app.utils.auth import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
    },
    "yandex": {
        "auth_url": "https://oauth.yandex.ru/authorize",
        "token_url": "https://oauth.yandex.ru/token",
        "user_info_url": "https://login.yandex.ru/info?format=json",
        "scope": "login:email",
    },
}


def get_provider_config(provider: str) -> dict:
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    return OAUTH_PROVIDERS[provider]


@router.get("/profile", response_model=UserOut)
async def get_auth_profile(
    current_user: User = Depends(get_current_user),
):
    """Получить профиль текущего пользователя."""
    return current_user


@router.get("/{provider}/login")
async def oauth_login(provider: str):
    config = get_provider_config(provider)

    client_id = settings.google_client_id if provider == "google" else settings.yandex_client_id
    redirect_uri = f"{settings.frontend_url}/auth/callback?provider={provider}"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": config["scope"],
    }

    query = "&".join(f"{k}={v}" for k, v in auth_params.items())
    auth_url = f"{config['auth_url']}?{query}"

    return {"url": auth_url}


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    config = get_provider_config(provider)

    client_id = settings.google_client_id if provider == "google" else settings.yandex_client_id
    client_secret = settings.google_client_secret if provider == "google" else settings.yandex_client_secret
    redirect_uri = f"{settings.frontend_url}/auth/callback?provider={provider}"

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
    provider_id = str(user_info.get("sub") or user_info.get("id"))

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by provider")

    # 3. Поиск или создание пользователя
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        user = User(
            email=email,
            hashed_password="",  # OAuth-пользователь без пароля
            is_active=True,
        )
        db.add(user)
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

    # 5. Генерация JWT
    jwt_token = create_access_token(data={"sub": user.email, "role": user.role.value})

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
    }
