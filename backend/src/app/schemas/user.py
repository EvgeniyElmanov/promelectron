from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AddressDetails(BaseModel):
    region: Optional[str] = None      # Область/край
    district: Optional[str] = None    # Район
    city: Optional[str] = None        # Город/населённый пункт
    street: Optional[str] = None      # Улица
    house: Optional[str] = None       # Дом/строение
    apartment: Optional[str] = None   # Квартира/офис


class UserCreate(BaseModel):
    email: str
    # F-13: max_length=128 prevents unbounded input (argon2 has no implicit truncation).
    password: str = Field(..., max_length=128)
    full_name: Optional[str] = None
    role: Optional[str] = "user"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    country_code: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    shipping_address: Optional[AddressDetails] = None
    role: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    country_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    shipping_address: Optional[AddressDetails] = None


class PasswordChange(BaseModel):
    # F-13: max_length=128 prevents unbounded input.
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class UserAddressCreate(BaseModel):
    label: Optional[str] = None
    country: Optional[str] = "Россия"
    city: str = Field(..., min_length=1, max_length=200)
    street: Optional[str] = None
    house: Optional[str] = None
    apartment: Optional[str] = None
    postal_code: Optional[str] = None
    cdek_location_code: Optional[int] = None
    cdek_delivery_point: Optional[str] = None
    is_default: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)


class UserAddressOut(BaseModel):
    id: int
    user_id: int
    label: Optional[str] = None
    country: str
    city: str
    street: Optional[str] = None
    house: Optional[str] = None
    apartment: Optional[str] = None
    postal_code: Optional[str] = None
    cdek_location_code: Optional[int] = None
    cdek_delivery_point: Optional[str] = None
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=1)
    # F-13: max_length=128 prevents unbounded input.
    new_password: str = Field(..., min_length=6, max_length=128)
