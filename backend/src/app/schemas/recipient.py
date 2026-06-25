from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CountryCode = Literal["RU", "KZ", "BY"]

NAME_REGEX = r'^[A-Za-zА-Яа-яЁё\- ]+$'
PHONE_REGEX = r'^\+7\d{10}$'


def _normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


class RecipientBase(BaseModel):
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=NAME_REGEX,
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=NAME_REGEX,
    )
    patronymic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=NAME_REGEX,
    )
    phone: str = Field(..., pattern=PHONE_REGEX)
    country_code: CountryCode = Field(default="RU")

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
        pattern=NAME_REGEX,
    )
    last_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=NAME_REGEX,
    )
    patronymic: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=NAME_REGEX,
    )
    phone: Optional[str] = Field(default=None, pattern=PHONE_REGEX)
    country_code: Optional[CountryCode] = None
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
