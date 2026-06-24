import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
import httpx
from urllib.parse import urlencode

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.models.social_account import SocialAccount
from src.app.schemas.user import PasswordResetConfirm, PasswordResetRequest, UserOut
from src.app.core.config import settings
from src.app.services.feature_flags import is_enabled
from src.app.services.oauth_state import delete_state, peek_state, create_state, generate_pkce_pair
from src.app.services.user_service import UserService, _token_for_user
from src.app.utils.auth import get_current_user

logger = logging.getLogger(__name__)

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

    # CSRF-защита (F-01) + PKCE (F-06): случайный одноразовый state и
    # code_verifier сохраняются server-side в Redis и привязываются к провайдеру.
    code_verifier, code_challenge = generate_pkce_pair()
    state = await create_state(provider, code_verifier)

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": config["scope"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        **config.get("extra_auth_params", {}),
    }

    auth_url = f"{config['auth_url']}?{urlencode(auth_params)}"

    return {"url": auth_url}


def _provider_email_verified(provider: str, user_info: dict) -> bool:
    """Считается ли email подтверждённым провайдером (F-03).

    Яндекс возвращает только подтверждённые email-адреса. Google отдаёт
    флаг ``verified_email`` (v2/userinfo) или ``email_verified`` (OIDC).
    """
    if provider == "yandex":
        return True
    return bool(user_info.get("email_verified") or user_info.get("verified_email"))


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    # Fix #4: peek without deleting so a transient provider failure doesn't
    # burn the one-time state. We delete only after a successful token exchange.
    state_data = await peek_state(state)
    if not state_data:
        raise HTTPException(
            status_code=400,
            detail="Сессия авторизации недействительна или истекла. Попробуйте войти снова.",
        )
    provider = state_data["provider"]
    code_verifier = state_data.get("code_verifier")

    config = get_provider_config(provider)
    client_id, client_secret = await get_provider_credentials(provider)
    redirect_uri = f"{settings.frontend_url}/auth/callback"

    # 1. Обмен кода на токен (с PKCE code_verifier)
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            config["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
        if token_resp.status_code != 200:
            # F-05: не отдаём ответ провайдера клиенту, только в server-side лог.
            # State is NOT deleted — caller can retry with the same state.
            logger.warning(
                "OAuth token exchange failed for %s: %s", provider, token_resp.text
            )
            raise HTTPException(
                status_code=400,
                detail="Не удалось завершить авторизацию. Попробуйте снова.",
            )
        token_data = token_resp.json()

    # Fix #4: token exchange succeeded — now burn the state to prevent replay.
    await delete_state(state)

    # Fix #6: guard access_token presence before bracket access.
    access_token = token_data.get("access_token")
    if not access_token:
        logger.warning(
            "OAuth token response for %s missing access_token: %s",
            provider,
            list(token_data.keys()),
        )
        raise HTTPException(
            status_code=400,
            detail="Не удалось завершить авторизацию. Попробуйте снова.",
        )

    # 2. Получение данных пользователя
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            config["user_info_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            logger.warning(
                "OAuth user info request failed for %s: %s", provider, user_resp.text
            )
            raise HTTPException(
                status_code=400,
                detail="Не удалось получить данные профиля. Попробуйте снова.",
            )
        user_info = user_resp.json()

    # Fix #1: explicit None checks — `or` short-circuits on falsy 0/False, which are
    # valid numeric IDs some providers return. str(None) == "None" collapses users.
    raw_provider_id = user_info.get("id")
    if raw_provider_id is None:
        raw_provider_id = user_info.get("sub")
    if raw_provider_id is None or raw_provider_id == "":
        logger.warning(
            "OAuth provider %s did not return id or sub in user_info keys: %s",
            provider,
            list(user_info.keys()),
        )
        raise HTTPException(
            status_code=400,
            detail="Не удалось получить данные профиля. Попробуйте снова.",
        )
    provider_id = str(raw_provider_id)

    email = user_info.get("email") or user_info.get("default_email")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by provider")

    # Fix #7: normalise email to lowercase for case-insensitive deduplication.
    email = email.lower()

    full_name = user_info.get("name") or user_info.get("real_name") or user_info.get("display_name")
    avatar_url = user_info.get("picture") or user_info.get("default_avatar_id")
    if avatar_url and provider == "yandex" and not avatar_url.startswith("http"):
        avatar_url = f"https://avatars.yandex.net/get-yapic/{avatar_url}/islands-200"

    # 3. Ищем уже привязанный соц-аккаунт — это безопасный путь «возврата».
    social_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.provider == provider,
            SocialAccount.provider_id == provider_id,
        )
    )
    social = social_result.scalars().first()

    if social:
        user_result = await db.execute(select(User).where(User.id == social.user_id))
        user = user_result.scalars().first()

        # Fix #5: user may be deleted without cascade; guard AttributeError.
        if user is None:
            raise HTTPException(
                status_code=400,
                detail="Не удалось завершить авторизацию. Попробуйте войти снова.",
            )
    else:
        # Нет привязки — ищем пользователя по email (Fix #7: case-insensitive).
        result = await db.execute(
            select(User).where(func.lower(User.email) == email)
        )
        user = result.scalars().first()

        if user:
            # F-03: автолинковка к существующему аккаунту только при
            # подтверждённом провайдером email — иначе риск захвата аккаунта.
            if not _provider_email_verified(provider, user_info):
                # Fix #10: corrected instruction — no "link in settings" ghost flow.
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Аккаунт с этим email уже существует. "
                        "Войдите обычным способом с тем же email."
                    ),
                )
        else:
            # Fix L-3: two concurrent first-time logins with the same email →
            # IntegrityError on the unique email index. Rollback and re-read.
            try:
                user = User(
                    email=email,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    hashed_password=None,  # OAuth-пользователь без пароля (F-11)
                    is_active=True,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            except IntegrityError:
                await db.rollback()
                result = await db.execute(
                    select(User).where(func.lower(User.email) == email)
                )
                user = result.scalars().first()
                if user is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Не удалось завершить авторизацию. Попробуйте снова.",
                    )

        # Привязываем соц-аккаунт (токен провайдера не храним — F-04).
        # Fix #8: handle race on unique(provider, provider_id) with IntegrityError.
        try:
            social = SocialAccount(
                user_id=user.id,
                provider=provider,
                provider_id=provider_id,
            )
            db.add(social)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            # Another request already inserted this social account — re-read it.
            social_result = await db.execute(
                select(SocialAccount).where(
                    SocialAccount.provider == provider,
                    SocialAccount.provider_id == provider_id,
                )
            )
            social = social_result.scalars().first()
            if social is None:
                raise HTTPException(
                    status_code=400,
                    detail="Не удалось завершить авторизацию. Попробуйте снова.",
                )
            user_result = await db.execute(select(User).where(User.id == social.user_id))
            user = user_result.scalars().first()
            if user is None:
                raise HTTPException(
                    status_code=400,
                    detail="Не удалось завершить авторизацию. Попробуйте войти снова.",
                )

    # Обновляем профиль, если поля пустые.
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

    # Fix #9: reuse shared helper so OAuth and email login return identical shape/expiry.
    access_token_jwt = _token_for_user(user)

    return {
        "access_token": access_token_jwt,
        "token_type": "bearer",
        "user": UserOut.model_validate(user),
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
