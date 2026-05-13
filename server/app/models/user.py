from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship

from server.app.db.database import Base


class RoleEnum(PyEnum):
    user = "user"
    admin = "admin"
    supplier = "supplier"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.user, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship to SocialAccount
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    