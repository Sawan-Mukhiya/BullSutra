import uuid
from datetime import date, datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Integer, BigInteger, Float, Numeric, Boolean, Date, DateTime,
    ForeignKey, CheckConstraint, Index, UniqueConstraint, func, SmallInteger, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from bullsutra.db.base import Base

class AgentSignalRow(Base):
    __tablename__ = "agent_signals"
    __table_args__ = (
        CheckConstraint("agent IN ('news', 'fundamentals', 'technicals', 'risk')", name="ck_agent_signals_agent"),
        CheckConstraint("origin IN ('live', 'backfill')", name="ck_agent_signals_origin"),
        UniqueConstraint("security_id", "as_of", "agent", "logic_version", "origin", name="uq_agent_signals_unique_key"),
        Index("ix_agent_signals_as_of", "as_of"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    agent: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    drivers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    risks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    flags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    logic_version: Mapped[str] = mapped_column(String(16), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SignalOutcome(Base):
    __tablename__ = "signal_outcomes"
    __table_args__ = (
        CheckConstraint("agent IN ('news', 'fundamentals', 'technicals', 'consensus')", name="ck_signal_outcomes_agent"),
        Index("ix_signal_outcomes_agent_realized_on", "agent", "realized_on"),
    )

    security_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[date] = mapped_column(Date, primary_key=True)
    agent: Mapped[str] = mapped_column(String(16), primary_key=True)
    horizon_days: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    logic_version: Mapped[str] = mapped_column(String(16), primary_key=True)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    forward_return: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    realized_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hit: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

class ResearchBriefRow(Base):
    __tablename__ = "research_briefs"
    __table_args__ = (
        CheckConstraint("label IN ('BUY', 'HOLD', 'SELL')", name="ck_research_briefs_label"),
        Index("ix_research_briefs_security_as_of_created", "security_id", text("as_of DESC"), text("created_at DESC")),
        Index("ix_research_briefs_created_at_desc", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    consensus_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    position_multiplier: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    conflicted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    brief: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    used_llm: Mapped[bool] = mapped_column(Boolean, nullable=False)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AgentWeights(Base):
    __tablename__ = "agent_weights"
    __table_args__ = (
        Index("ix_agent_weights_scope_fitted_on_desc", "scope", text("fitted_on DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    fitted_on: Mapped[date] = mapped_column(Date, nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    calibrator: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
