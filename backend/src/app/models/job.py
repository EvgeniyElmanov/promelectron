from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList

from src.app.db.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    payload = Column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)
    processing_log = Column(MutableList.as_mutable(ARRAY(String)), nullable=False, default=list)
    run_after = Column(DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    deadline = Column(DateTime(timezone=True), nullable=True, index=True)
    timeout = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )
