import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from src.app.db.database import get_db
from src.app.models.user import RoleEnum, User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str):
    # F-13: argon2 has no 72-byte truncation limit — hash the full password.
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # F-07: include a unique jti so tokens can be individually revoked.
    jti = secrets.token_urlsafe(16)
    to_encode.update({"exp": expire, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        # F-10: sub is now the stable numeric user id (str).
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        try:
            user_id = int(sub)
        except (ValueError, TypeError):
            raise credentials_exception
        # F-07: check jti denylist (tokens logged out are rejected).
        from src.app.services.token_denylist import is_revoked

        jti: str = payload.get("jti")
        if await is_revoked(jti):
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    # F-10: removed db.refresh — select already returns a fresh row.
    return user


async def get_optional_user(
    token: HTTPAuthorizationCredentials = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if token is None:
        return None
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        # F-10: sub is now the stable numeric user id (str).
        sub: str = payload.get("sub")
        if sub is None:
            return None
        try:
            user_id = int(sub)
        except (ValueError, TypeError):
            return None
        # F-07: check jti denylist.
        from src.app.services.token_denylist import is_revoked

        jti: str = payload.get("jti")
        if await is_revoked(jti):
            return None
    except JWTError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        return None
    # F-10: removed db.refresh — select already returns a fresh row.
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_admin(
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    return current_user


async def get_current_active_supplier(
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != RoleEnum.supplier:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    return current_user
