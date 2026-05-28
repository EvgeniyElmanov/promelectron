import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from src.app.utils.rate_limiter import conditional_limit
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.user import PasswordChange, UserCreate, UserOut, UserUpdate
from src.app.services.user_service import UserService
from src.app.services.storage_service import storage
from src.app.utils.auth import (
    get_current_active_admin,
    get_current_active_supplier,
    get_current_user,
)

AVATAR_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

router = APIRouter()


@router.post("/register")
@conditional_limit("50/minute")
async def register_user(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await UserService.register_user(user_data=user_data, db=db)


@router.post("/login")
@conditional_limit("50/minute")
async def login_user(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await UserService.login_user(user_data=user_data, db=db)


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_users_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await UserService.update_profile(
        user_id=current_user.id, user_data=user_data, db=db
    )


@router.patch("/me/password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await UserService.change_password(
        user_id=current_user.id, password_data=password_data, db=db
    )


@router.get("/profile", response_model=UserOut)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/admin")
async def read_admin_data(current_user: User = Depends(get_current_active_admin)):
    return {"message": f"Hello admin {current_user.email}"}


@router.get("/supplier")
async def read_supplier_data(current_user: User = Depends(get_current_active_supplier)):
    return {"message": f"Hello supplier {current_user.email}"}


@router.post("/me/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in AVATAR_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(AVATAR_ALLOWED_EXTENSIONS)}",
        )

    # Remove old avatar file if exists (including variants)
    if current_user.avatar_url:
        await storage.delete_image(current_user.avatar_url)

    key = f"avatars/{current_user.id}/{uuid.uuid4().hex}{ext}"
    result = await storage.upload_image(key, file)

    user = await UserService.update_profile(
        user_id=current_user.id,
        user_data=UserUpdate(avatar_url=result["original"]),
        db=db,
    )

    response_data = UserOut.model_validate(user).model_dump()
    response_data.update({
        "original": result["original"],
        "small": result["small"],
        "medium": result["medium"],
        "large": result["large"],
    })
    return response_data
