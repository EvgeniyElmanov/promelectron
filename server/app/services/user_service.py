from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from server.app.models.user import User
from server.app.schemas.user import UserCreate
from server.app.utils.auth import create_access_token, hash_password, verify_password


class UserService:
    @staticmethod
    async def register_user(user_data: UserCreate, db: AsyncSession) -> User:
        result = await db.execute(select(User).where(User.email == user_data.email))
        user = result.scalars().first()
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_pw = hash_password(user_data.password)
        new_user = User(email=user_data.email, hashed_password=hashed_pw, role="user")
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def login_user(user_data: UserCreate, db: AsyncSession) -> dict[str, str]:
        result = await db.execute(select(User).where(User.email == user_data.email))
        user = result.scalars().first()
        if not user or not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
