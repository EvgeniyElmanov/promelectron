from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.app.db.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OnecChangeLog(Base):
    __tablename__ = "onec_change_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), nullable=False, index=True, unique=True, default=uuid4)
    entity_type = Column(String(50), nullable=False, index=True)
    source = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=False)
    payload_size_bytes = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)


class OnecIntakeLog(Base):
    """Журнал приёма сырых выгрузок 1С (Фаза 1, #118).

    Диагностические поля headers/query_params/error заполняются на приёме
    и используются при разборе неизвестных форматов 1С (Фаза 3, #119).
    """

    __tablename__ = "onec_intake_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    intake_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True, default=uuid4)
    bucket = Column(String(128), nullable=False)
    object_key = Column(String(512), nullable=False)
    content_type = Column(String(255), nullable=True)
    received_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    headers = Column(JSONB, nullable=True)
    query_params = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    remote_addr = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    # Значения "parsed"/"failed" добавляются в Фазе 4 (#120) —
    # поле строковое, миграция схемы НЕ требуется, только новые литералы.
    status = Column(String(20), nullable=False, default="received", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
