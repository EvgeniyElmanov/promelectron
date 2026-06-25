from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from src.app.models.recipient import Recipient
from src.app.models.supplier import Supplier
from src.app.models.user import PasswordResetToken, User, UserAddress
from src.app.schemas.user import UserAddressCreate, UserCreate, UserOut
from src.app.utils.auth import create_access_token, hash_password, verify_password


def _token_for_user(user: User) -> str:
    # F-10: sub is the stable numeric user id, not email.
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": str(user.id), "role": user.role.value}, expires_delta=access_token_expires
    )


class UserService:
    @staticmethod
    async def register_user(user_data: UserCreate, db: AsyncSession) -> dict:
        # M-2: normalise email to lowercase before duplicate-check and storage
        # so "Alice@x.com" and "alice@x.com" are treated as one account.
        email = user_data.email.lower()
        result = await db.execute(
            select(User).where(func.lower(User.email) == email)
        )
        user = result.scalars().first()
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Prevent self-registration as admin
        role = user_data.role or "user"
        if role == "admin":
            role = "user"

        hashed_pw = hash_password(user_data.password)
        new_user = User(
            email=email,
            hashed_password=hashed_pw,
            full_name=user_data.full_name,
            role=role,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Auto-create Supplier record for supplier role
        if role == "supplier":
            supplier = Supplier(
                user_id=new_user.id,
                name=new_user.full_name or new_user.email.split("@")[0],
                description="",
                api_key=str(uuid4()),
                is_active=True,
            )
            db.add(supplier)
            await db.commit()

        access_token = _token_for_user(new_user)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserOut.model_validate(new_user),
        }

    @staticmethod
    async def login_user(user_data: UserCreate, db: AsyncSession) -> dict:
        result = await db.execute(select(User).where(User.email == user_data.email))
        user = result.scalars().first()
        # F-11: у OAuth-пользователей нет пароля (hashed_password is None) —
        # парольный вход для них запрещён. Проверяем явно до verify_password,
        # т.к. passlib бросает исключение на пустом/None-хеше.
        if (
            not user
            or not user.hashed_password
            or not verify_password(user_data.password, user.hashed_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = _token_for_user(user)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserOut.model_validate(user),
        }

    @staticmethod
    async def update_profile(user_id: int, user_data, db: AsyncSession) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user_data.email is not None and user_data.email.lower() != user.email:
            # M-2: normalise on write; duplicate-check is case-insensitive.
            new_email = user_data.email.lower()
            existing = await db.execute(
                select(User).where(func.lower(User.email) == new_email)
            )
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="Email already in use")
            user.email = new_email

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        names_changed = False
        if user_data.first_name is not None:
            user.first_name = user_data.first_name
            names_changed = True

        if user_data.last_name is not None:
            user.last_name = user_data.last_name
            names_changed = True

        if names_changed:
            new_full_name = " ".join(
                filter(None, [user.first_name, user.last_name])
            ).strip()
            if new_full_name:
                user.full_name = new_full_name

        if user_data.patronymic is not None:
            user.patronymic = user_data.patronymic

        if user_data.country_code is not None:
            user.country_code = user_data.country_code

        if user_data.phone is not None:
            user.phone = user_data.phone

        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url

        if user_data.shipping_address is not None:
            user.shipping_address = (
                user_data.shipping_address.model_dump() if user_data.shipping_address else None
            )

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_password(user_id: int, password_data, db: AsyncSession) -> dict:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # F-11 guard: OAuth-users have no password — prevent passlib crash on None hash.
        if not user.hashed_password:
            raise HTTPException(
                status_code=400,
                detail="У вас нет установленного пароля — вы вошли через соцсеть.",
            )

        if not verify_password(password_data.old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect old password")

        user.hashed_password = hash_password(password_data.new_password)
        await db.commit()
        return {"message": "Password updated successfully"}

    @staticmethod
    async def get_or_create_from_guest(
        email: str,
        first_name: str,
        last_name: str,
        phone: str | None,
        db: AsyncSession,
        patronymic: str | None = None,
        country_code: str = "RU",
    ) -> tuple[User, bool, str]:
        """Получить существующего пользователя или создать из данных гостя.

        Возвращает (user, created, temp_password).
        """
        email = email.lower()
        result = await db.execute(
            select(User).where(func.lower(User.email) == email).with_for_update()
        )
        user = result.scalars().first()

        if user:
            # Обновляем пустие поля данными из чекаута
            updated = False
            full_name = f"{first_name} {last_name}".strip()
            if full_name and not user.full_name:
                user.full_name = full_name
                updated = True
            if first_name and not user.first_name:
                user.first_name = first_name
                updated = True
            if last_name and not user.last_name:
                user.last_name = last_name
                updated = True
            if patronymic and not user.patronymic:
                user.patronymic = patronymic
                updated = True
            if country_code and not user.country_code:
                user.country_code = country_code
                updated = True
            if phone and not user.phone:
                user.phone = phone
                updated = True
            if updated:
                await db.commit()
                await db.refresh(user)
            return user, False, ""

        temp_password = uuid4().hex[:16]
        full_name = f"{first_name} {last_name}".strip()
        new_user = User(
            email=email,
            hashed_password=hash_password(temp_password),
            full_name=full_name or None,
            first_name=first_name or None,
            last_name=last_name or None,
            patronymic=patronymic or None,
            country_code=country_code or "RU",
            phone=phone,
            role="user",
            is_active=True,
        )
        db.add(new_user)
        try:
            await db.commit()
            await db.refresh(new_user)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(User).where(func.lower(User.email) == email))
            existing_user = result.scalars().first()
            if existing_user:
                updated = False
                if full_name and not existing_user.full_name:
                    existing_user.full_name = full_name
                    updated = True
                if first_name and not existing_user.first_name:
                    existing_user.first_name = first_name
                    updated = True
                if last_name and not existing_user.last_name:
                    existing_user.last_name = last_name
                    updated = True
                if patronymic and not existing_user.patronymic:
                    existing_user.patronymic = patronymic
                    updated = True
                if country_code and not existing_user.country_code:
                    existing_user.country_code = country_code
                    updated = True
                if phone and not existing_user.phone:
                    existing_user.phone = phone
                    updated = True
                if updated:
                    await db.commit()
                    await db.refresh(existing_user)
                return existing_user, False, ""
            raise

        # Создаём получателя по умолчанию из данных заказа
        default_recipient = Recipient(
            user_id=new_user.id,
            first_name=first_name,
            last_name=last_name,
            patronymic=patronymic,
            phone=phone or "+70000000000",
            country_code=country_code or "RU",
            is_default=True,
        )
        db.add(default_recipient)
        await db.commit()

        return new_user, True, temp_password

    @staticmethod
    async def save_address(user_id: int, address_data: UserAddressCreate, db: AsyncSession) -> UserAddress:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if address_data.is_default:
            # Снимаем флаг is_default с остальных адресов
            existing_defaults = await db.execute(
                select(UserAddress).where(
                    UserAddress.user_id == user_id, UserAddress.is_default.is_(True)
                )
            )
            for addr in existing_defaults.scalars().all():
                addr.is_default = False

        address = UserAddress(
            user_id=user_id,
            label=address_data.label,
            country=address_data.country or "Россия",
            city=address_data.city,
            street=address_data.street,
            house=address_data.house,
            apartment=address_data.apartment,
            postal_code=address_data.postal_code,
            cdek_location_code=address_data.cdek_location_code,
            cdek_delivery_point=address_data.cdek_delivery_point,
            is_default=address_data.is_default,
        )
        db.add(address)
        await db.commit()
        await db.refresh(address)
        return address

    @staticmethod
    async def list_addresses(user_id: int, db: AsyncSession) -> list[UserAddress]:
        result = await db.execute(
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_password_reset_token(user_id: int, db: AsyncSession) -> str:
        """Создать одноразовый токен сброса пароля. Возвращает plaintext токен."""
        token = uuid4().hex
        token_hash = hash_password(token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()
        await db.refresh(reset_token)
        return token

    @staticmethod
    async def reset_password(token: str, new_password: str, db: AsyncSession) -> dict:
        """Сбросить пароль по одноразовому токену."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(PasswordResetToken)
            .where(
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
            .order_by(PasswordResetToken.created_at.desc())
        )
        tokens = result.scalars().all()

        for reset_token in tokens:
            if verify_password(token, reset_token.token_hash):
                if reset_token.is_expired():
                    raise HTTPException(status_code=400, detail="Token expired")

                user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
                user = user_result.scalars().first()
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")

                user.hashed_password = hash_password(new_password)
                now = datetime.now(timezone.utc)
                reset_token.used_at = now
                # Invalidate all other unused tokens for the same user
                await db.execute(
                    update(PasswordResetToken)
                    .where(
                        PasswordResetToken.user_id == user.id,
                        PasswordResetToken.used_at.is_(None),
                        PasswordResetToken.id != reset_token.id,
                    )
                    .values(used_at=now)
                )
                await db.commit()
                return {"message": "Password reset successfully"}

        raise HTTPException(status_code=400, detail="Invalid or expired token")
