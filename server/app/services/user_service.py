from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from server.app.models.user import User
from server.app.schemas.user import UserCreate, UserOut
from server.app.utils.auth import create_access_token, hash_password, verify_password


def _token_for_user(user: User) -> str:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": user.email, "role": user.role.value}, expires_delta=access_token_expires
    )


class UserService:
    @staticmethod
    async def register_user(user_data: UserCreate, db: AsyncSession) -> dict:
        result = await db.execute(select(User).where(User.email == user_data.email))
        user = result.scalars().first()
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_pw = hash_password(user_data.password)
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_pw,
            full_name=user_data.full_name,
            role="user",
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

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
        if not user or not verify_password(user_data.password, user.hashed_password):
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

        if user_data.email is not None and user_data.email != user.email:
            existing = await db.execute(select(User).where(User.email == user_data.email))
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="Email already in use")
            user.email = user_data.email

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_password(user_id: int, password_data, db: AsyncSession) -> dict:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(password_data.old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect old password")

        user.hashed_password = hash_password(password_data.new_password)
        await db.commit()
        return {"message": "Password updated successfully"}
