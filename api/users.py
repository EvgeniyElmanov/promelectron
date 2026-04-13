from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserOut
from utils.auth import (
    verify_password,
    create_access_token,
    get_current_user,
    get_current_active_user,
    get_current_active_admin,
    get_current_active_supplier,
)
from config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверим, существует ли уже пользователь
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    user = result.scalars().first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Импортируй hash_password в начале файла, если ещё не сделал
    from utils.auth import hash_password

    hashed_pw = hash_password(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pw, role="user")
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login")
async def login_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Найдём пользователя по email
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
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

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/admin")
async def read_admin_data(current_user: User = Depends(get_current_active_admin)):
    return {"message": f"Hello admin {current_user.email}"}

@router.get("/supplier")
async def read_supplier_data(current_user: User = Depends(get_current_active_supplier)):
    return {"message": f"Hello supplier {current_user.email}"}