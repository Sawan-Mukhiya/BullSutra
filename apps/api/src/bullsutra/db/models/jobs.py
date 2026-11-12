import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Integer, BigInteger, Float, DateTime, ForeignKey,
    CheckConstraint, Index, UniqueConstraint, func, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bullsutra.db.base import Base

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('research', 'backtest', 'eod_prices', 'news_scrape', 'news_score', "
            "'fundamentals_import', 'signals_daily', 'weights_update', 'signals_backfill')",
            name="ck_jobs_kind"
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_jobs_status"
        ),
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_kind_created_at_desc", "kind", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["JobEvent"]] = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")

class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (
        UniqueConstraint("job_id", "seq", name="uq_job_events_job_id_seq"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    node: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job: Mapped[Job] = relationship("Job", back_populates="events")
