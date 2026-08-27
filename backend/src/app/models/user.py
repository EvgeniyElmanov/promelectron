from datetime import datetime, timezone
from enum import Enum as PyEnum

import sqlalchemy as sa
from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from src.app.db.database import Base


class RoleEnum(PyEnum):
    user = "user"
    admin = "admin"
    supplier = "supplier"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    patronymic = Column(String, nullable=True)
    country_code = Column(String, nullable=True, default="RU")
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    shipping_address = Column(JSON, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.user, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        server_default=sa.false(),
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship to SocialAccount
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")
    recipients = relationship("Recipient", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="EmailVerificationToken.created_at.desc()",
    )


class UserAddress(Base):
    __tablename__ = "user_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String, nullable=True)
    country = Column(String, nullable=False, default="Россия")
    city = Column(String, nullable=False)
    street = Column(String, nullable=True)
    house = Column(String, nullable=True)
    apartment = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    cdek_location_code = Column(Integer, nullable=True)
    cdek_delivery_point = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="addresses")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="password_reset_tokens")

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    def is_valid(self) -> bool:
        return self.used_at is None and not self.is_expired()


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        Index(
            "ix_email_verification_tokens_user_id_created_at",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_email_verification_tokens_expires_at",
            "expires_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="email_verification_tokens")
