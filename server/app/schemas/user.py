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
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "user"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    shipping_address: Optional[AddressDetails] = None
    role: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    shipping_address: Optional[AddressDetails] = None


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
