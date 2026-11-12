import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Integer, BigInteger, DateTime, CheckConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from bullsutra.db.base import Base

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'succeeded', 'failed', 'partial')", name="ck_ingestion_runs_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rows_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

class Upload(Base):
    __tablename__ = "uploads"
    __table_args__ = (
        CheckConstraint("upload_type IN ('prices_csv', 'fundamentals_csv')", name="ck_uploads_upload_type"),
        CheckConstraint("status IN ('validated', 'rejected', 'committed')", name="ck_uploads_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_type: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="validated")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    staged_path: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    committed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class LlmCache(Base):
    __tablename__ = "llm_cache"
    __table_args__ = (
        Index("ix_llm_cache_created_at", "created_at"),
    )

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
