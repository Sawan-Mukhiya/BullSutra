from datetime import date, datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Integer, BigInteger, Numeric, Boolean, Date, DateTime,
    CheckConstraint, Index, func, SmallInteger
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from bullsutra.db.base import Base

class QuarterlyFinancial(Base):
    __tablename__ = "quarterly_financials"
    __table_args__ = (
        CheckConstraint("quarter BETWEEN 1 AND 4", name="ck_quarterly_financials_quarter_1_to_4"),
        CheckConstraint("eps_basis IN ('annualized', 'ytd', 'quarter', 'unknown')", name="ck_quarterly_financials_eps_basis"),
        Index("ix_quarterly_financials_symbol_usable_from", "symbol", "usable_from"),
    )

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(16), primary_key=True)
    quarter: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    is_restated: Mapped[bool] = mapped_column(Boolean, primary_key=True, default=False)

    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    announced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usable_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    revenue: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    net_profit: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    eps_reported: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    eps_basis: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    eps_ytd: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    eps_annualized: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    eps_ttm: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    bvps: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    paid_up_capital: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    shares_outstanding_est: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    roe_annualized: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    pe_reported: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    npl_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    unit_multiplier_applied: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    field_sources: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ValuationDaily(Base):
    __tablename__ = "valuation_daily"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    pe_pit: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    pe_ttm_pit: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    pb_pit: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    pe_reported: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
