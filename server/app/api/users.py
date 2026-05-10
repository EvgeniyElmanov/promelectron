from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.models.user import User
from server.app.schemas.user import UserCreate, UserOut
from server.app.services.user_service import UserService
from server.app.utils.auth import (
    get_current_active_admin,
    get_current_active_supplier,
    get_current_user,
)

router = APIRouter()


@router.post("/register", response_model=UserOut)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await UserService.register_user(user_data=user_data, db=db)


@router.post("/login")
async def login_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await UserService.login_user(user_data=user_data, db=db)


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/profile", response_model=UserOut)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/admin")
async def read_admin_data(current_user: User = Depends(get_current_active_admin)):
    return {"message": f"Hello admin {current_user.email}"}


@router.get("/supplier")
async def read_supplier_data(current_user: User = Depends(get_current_active_supplier)):
    return {"message": f"Hello supplier {current_user.email}"}

