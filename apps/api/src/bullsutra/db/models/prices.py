from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, Numeric, Boolean, Date, DateTime,
    ForeignKey, CheckConstraint, Index, UniqueConstraint, func, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bullsutra.db.base import Base

class DailyBar(Base):
    __tablename__ = "daily_bars"
    __table_args__ = (
        CheckConstraint("volume >= 0", name="ck_daily_bars_volume_positive"),
        CheckConstraint("turnover >= 0", name="ck_daily_bars_turnover_positive"),
        CheckConstraint("bar_status IN ('provisional', 'final')", name="ck_daily_bars_bar_status"),
        CheckConstraint("quality_tier IN ('A', 'B', 'C')", name="ck_daily_bars_quality_tier"),
        UniqueConstraint("symbol", "trade_date", name="uq_daily_bars_symbol_trade_date"),
        Index("ix_daily_bars_trade_date", "trade_date"),
        Index("ix_daily_bars_symbol_trade_date", "symbol", "trade_date"),
    )

    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    open: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    turnover: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False, default=0.0)
    trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prev_close_exchange: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    bar_source: Mapped[str] = mapped_column(String(32), nullable=False)
    bar_status: Mapped[str] = mapped_column(String(16), nullable=False, default="final")
    quality_tier: Mapped[str] = mapped_column(String(4), nullable=False, default="A")
    bar_completeness: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=1.0000)
    ohlc_flags: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    regime_id: Mapped[str] = mapped_column(String(16), nullable=False)
    limit_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    ref_price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    upper_limit_price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    lower_limit_price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    hit_upper: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hit_lower: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_upper: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_lower: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ret_over_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AdjEvent(Base):
    __tablename__ = "adj_events"
    __table_args__ = (
        CheckConstraint("step_factor >= 1.0", name="ck_adj_events_step_factor_ge_1"),
        CheckConstraint("event_type IN ('bonus', 'bonus_cash', 'right', 'unexplained_step')", name="ck_adj_events_event_type"),
        CheckConstraint("method IN ('exchange_step_s4', 'ledger_formula', 'exchange_prev_close')", name="ck_adj_events_method"),
        CheckConstraint("status IN ('verified', 'unverified', 'review_queue')", name="ck_adj_events_status"),
        UniqueConstraint("symbol", "ex_date", name="uq_adj_events_symbol_ex_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    step_factor: Mapped[float] = mapped_column(Numeric(18, 10), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    ledger_bonus_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    ledger_cash_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    ledger_right_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="verified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SnapshotNepsepyDaily(Base):
    __tablename__ = "snapshot_nepsepy_daily"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    market_capitalization: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    fifty_two_week_high: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    fifty_two_week_low: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    last_updated_price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    last_updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    average_traded_price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    previous_day_close_price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)

class FloorsheetDailyAgg(Base):
    __tablename__ = "floorsheet_daily_agg"
    __table_args__ = (
        Index("ix_floorsheet_daily_agg_trade_date", "trade_date"),
    )

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    n_contracts: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_contract_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    median_contract_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    block_share: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    small_lot_share: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    top5_buyer_share: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    top5_seller_share: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    buyer_hhi: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    seller_hhi: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    n_buyer_brokers: Mapped[int] = mapped_column(Integer, nullable=False)
    n_seller_brokers: Mapped[int] = mapped_column(Integer, nullable=False)
    bar_completeness: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
