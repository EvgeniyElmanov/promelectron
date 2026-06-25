from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value


class RecipientBase(BaseModel):
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    patronymic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    phone: str = Field(..., pattern=r'^\+7\d{10}$')
    country_code: str = Field(default="RU", max_length=3)

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @field_validator("first_name", "last_name", "patronymic", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return _normalize_name(value)


class RecipientCreate(RecipientBase):
    is_default: bool = False


class RecipientUpdate(BaseModel):
    first_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    last_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    patronymic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r'^[A-Za-zА-Яа-яЁё\- ]+$',
    )
    phone: Optional[str] = Field(default=None, pattern=r'^\+7\d{10}$')
    country_code: Optional[str] = Field(default=None, max_length=3)
    is_default: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @field_validator("first_name", "last_name", "patronymic", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return _normalize_name(value)


class RecipientOut(RecipientBase):
    id: int
    user_id: Optional[int] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
