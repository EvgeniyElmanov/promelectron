from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.app.db.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_batch_id() -> str:
    return str(uuid4())


class OnecChangeLog(Base):
    __tablename__ = "onec_change_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), nullable=False, index=True, default=uuid4)
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
