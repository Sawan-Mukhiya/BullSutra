import uuid
from datetime import date, datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Integer, BigInteger, Numeric, Boolean, Date, DateTime,
    ForeignKey, CheckConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from bullsutra.db.base import Base

class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_backtest_runs_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class BacktestStrategyResult(Base):
    __tablename__ = "backtest_strategy_results"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), primary_key=True)
    strategy_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    is_benchmark: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    bootstrap: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

class BacktestEquity(Base):
    __tablename__ = "backtest_equity"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), primary_key=True)
    strategy_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    equity: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    drawdown: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    exposure: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    __table_args__ = (
        CheckConstraint("exit_reason IN ('signal', 'end_of_test', 'delisted', 'stop_loss')", name="ck_backtest_trades_exit_reason"),
        Index("ix_backtest_trades_run_id_strategy_key", "run_id", "strategy_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(64), nullable=False)
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    entry_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_pnl: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    costs: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0.0)
    tax: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0.0)
    net_pnl: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    return_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    holding_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exit_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

class BacktestFold(Base):
    __tablename__ = "backtest_folds"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("backtest_runs.id", ondelete="CASCADE"), primary_key=True)
    fold_idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    train_start: Mapped[date] = mapped_column(Date, nullable=False)
    train_end: Mapped[date] = mapped_column(Date, nullable=False)
    test_start: Mapped[date] = mapped_column(Date, nullable=False)
    test_end: Mapped[date] = mapped_column(Date, nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    calibrator: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
