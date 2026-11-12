from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, Numeric, Boolean, Date, DateTime,
    ForeignKey, CheckConstraint, Index, func, SmallInteger
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bullsutra.db.base import Base

class ReferenceSymbol(Base):
    __tablename__ = "securities"
    __table_args__ = (
        CheckConstraint("symbol = upper(symbol)", name="ck_securities_symbol_upper"),
        CheckConstraint("sector_group IN ('bank','hydro','insurance','other')", name="ck_securities_sector_group"),
        CheckConstraint("instrument_type IN ('equity','mutual_fund','debenture','promoter','other')", name="ck_securities_instrument_type"),
        Index("ix_securities_in_universe", "in_universe"),
        Index("ix_securities_sector_group", "sector_group"),
        Index("ix_securities_symbol", "symbol"),
        Index("ix_securities_nepse_security_id", "nepse_security_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    nepse_security_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str] = mapped_column(String, nullable=False, default="Others")
    sector_group: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    exchange_sector: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    instrument_type: Mapped[str] = mapped_column(String(32), nullable=False, default="equity")
    instrument_class: Mapped[str] = mapped_column(String(32), nullable=False, default="equity")
    listed_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    delisted_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    first_bar_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_bar_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    merged_into_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("securities.id", ondelete="SET NULL"), nullable=True)
    in_universe: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    merged_into: Mapped[Optional["ReferenceSymbol"]] = relationship("ReferenceSymbol", remote_side=[id])

class SymbolAlias(Base):
    __tablename__ = "symbol_alias"
    __table_args__ = (
        CheckConstraint("kind IN ('rename', 'merger', 'acquisition')", name="ck_symbol_alias_kind"),
    )

    old_symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    effective_date: Mapped[date] = mapped_column(Date, primary_key=True)
    new_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)

class DimTradingDay(Base):
    __tablename__ = "dim_trading_day"
    __table_args__ = (
        CheckConstraint("regime_id IN ('regime_1', 'regime_2', 'regime_3')", name="ck_dim_trading_day_regime_id"),
        Index("ix_dim_trading_day_session_idx", "session_idx"),
        Index("ix_dim_trading_day_regime_id", "regime_id"),
    )

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    is_session: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_holiday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    holiday_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dow: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Mon, 6=Sun
    regime_id: Mapped[str] = mapped_column(String(16), nullable=False)
    trading_week_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_idx: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sessions_since_regime_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_transition_week: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stock_limit_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    preopen_limit_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    order_band_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    mkt_breaker_id: Mapped[str] = mapped_column(String(16), nullable=False)
    after_market_orders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    __table_args__ = (
        CheckConstraint("action_type IN ('bonus', 'right', 'cash', 'combined')", name="ck_corporate_actions_action_type"),
        CheckConstraint("ex_date_status IN ('observed', 'from_bookclose', 'pending')", name="ck_corporate_actions_ex_date_status"),
        Index("ix_corporate_actions_symbol_ex_date", "symbol", "ex_date"),
        Index("ix_corporate_actions_usable_from", "usable_from"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(16), nullable=False)
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)
    announced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usable_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    bookclose_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ex_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cash_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    bonus_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    right_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    right_ratio_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    right_ratio_den: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    right_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    document_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ex_date_status: Mapped[str] = mapped_column(String(20), nullable=False, default="observed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class IndexDaily(Base):
    __tablename__ = "index_daily"

    index_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    index_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    open: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    turnover: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    percentage_change: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

class SectorIndexDaily(Base):
    __tablename__ = "sector_index_daily"

    index_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    index_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    open: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    turnover: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    percentage_change: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

class UniverseMembership(Base):
    __tablename__ = "universe_membership"
    __table_args__ = (
        Index("ix_universe_membership_month_in_universe", "month_start", "in_universe"),
    )

    month_start: Mapped[date] = mapped_column(Date, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    median_turnover_250: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    trading_presence_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    in_universe: Mapped[bool] = mapped_column(Boolean, nullable=False)
