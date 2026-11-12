"""Initial migration for BullSutra schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-26 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 0. Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('admin')", name="ck_users_role_admin"),
    )

    # 2. api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False, unique=True),
        sa.Column("role", sa.String(), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('admin')", name="ck_api_keys_role_admin"),
    )

    # 3. securities
    op.create_table(
        "securities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False, unique=True),
        sa.Column("nepse_security_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sector", sa.String(), nullable=False, server_default="Others"),
        sa.Column("sector_group", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("exchange_sector", sa.String(length=64), nullable=True),
        sa.Column("instrument_type", sa.String(length=32), nullable=False, server_default="equity"),
        sa.Column("instrument_class", sa.String(length=32), nullable=False, server_default="equity"),
        sa.Column("listed_on", sa.Date(), nullable=True),
        sa.Column("delisted_on", sa.Date(), nullable=True),
        sa.Column("first_bar_date", sa.Date(), nullable=True),
        sa.Column("last_bar_date", sa.Date(), nullable=True),
        sa.Column("merged_into_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("in_universe", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("symbol = upper(symbol)", name="ck_securities_symbol_upper"),
        sa.CheckConstraint("sector_group IN ('bank','hydro','insurance','other')", name="ck_securities_sector_group"),
        sa.CheckConstraint("instrument_type IN ('equity','mutual_fund','debenture','promoter','other')", name="ck_securities_instrument_type"),
    )
    op.create_index("ix_securities_in_universe", "securities", ["in_universe"])
    op.create_index("ix_securities_sector_group", "securities", ["sector_group"])
    op.create_index("ix_securities_symbol", "securities", ["symbol"])
    op.create_index("ix_securities_nepse_security_id", "securities", ["nepse_security_id"])

    # 4. symbol_alias
    op.create_table(
        "symbol_alias",
        sa.Column("old_symbol", sa.String(length=32), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("new_symbol", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("old_symbol", "effective_date", name="pk_symbol_alias"),
        sa.CheckConstraint("kind IN ('rename', 'merger', 'acquisition')", name="ck_symbol_alias_kind"),
    )

    # 5. dim_trading_day
    op.create_table(
        "dim_trading_day",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("is_session", sa.Boolean(), nullable=False),
        sa.Column("is_holiday", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("holiday_name", sa.String(), nullable=True),
        sa.Column("dow", sa.SmallInteger(), nullable=False),
        sa.Column("regime_id", sa.String(length=16), nullable=False),
        sa.Column("trading_week_id", sa.Integer(), nullable=False),
        sa.Column("session_idx", sa.Integer(), nullable=True),
        sa.Column("sessions_since_regime_start", sa.Integer(), nullable=True),
        sa.Column("is_transition_week", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stock_limit_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("preopen_limit_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("order_band_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("mkt_breaker_id", sa.String(length=16), nullable=False),
        sa.Column("after_market_orders", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("regime_id IN ('regime_1', 'regime_2', 'regime_3')", name="ck_dim_trading_day_regime_id"),
    )
    op.create_index("ix_dim_trading_day_session_idx", "dim_trading_day", ["session_idx"])
    op.create_index("ix_dim_trading_day_regime_id", "dim_trading_day", ["regime_id"])

    # 6. daily_bars
    op.create_table(
        "daily_bars",
        sa.Column("security_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("open", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("high", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("low", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("close", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("turnover", sa.Numeric(precision=20, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("trades", sa.Integer(), nullable=True),
        sa.Column("prev_close_exchange", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("bar_source", sa.String(length=32), nullable=False),
        sa.Column("bar_status", sa.String(length=16), nullable=False, server_default="final"),
        sa.Column("quality_tier", sa.String(length=4), nullable=False, server_default="A"),
        sa.Column("bar_completeness", sa.Numeric(precision=6, scale=4), nullable=False, server_default="1.0000"),
        sa.Column("ohlc_flags", sa.String(), nullable=True),
        sa.Column("regime_id", sa.String(length=16), nullable=False),
        sa.Column("limit_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("ref_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("upper_limit_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("lower_limit_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("hit_upper", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hit_lower", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("locked_upper", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("locked_lower", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ret_over_limit", sa.Float(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("volume >= 0", name="ck_daily_bars_volume_positive"),
        sa.CheckConstraint("turnover >= 0", name="ck_daily_bars_turnover_positive"),
        sa.CheckConstraint("bar_status IN ('provisional', 'final')", name="ck_daily_bars_bar_status"),
        sa.CheckConstraint("quality_tier IN ('A', 'B', 'C')", name="ck_daily_bars_quality_tier"),
        sa.UniqueConstraint("symbol", "trade_date", name="uq_daily_bars_symbol_trade_date"),
    )
    op.create_index("ix_daily_bars_trade_date", "daily_bars", ["trade_date"])
    op.create_index("ix_daily_bars_symbol_trade_date", "daily_bars", ["symbol", "trade_date"])

    # Create legacy view daily_prices
    op.execute("CREATE OR REPLACE VIEW daily_prices AS SELECT * FROM daily_bars;")

    # 7. adj_events
    op.create_table(
        "adj_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("step_factor", sa.Numeric(precision=18, scale=10), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("ledger_bonus_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("ledger_cash_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("ledger_right_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="verified"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("step_factor >= 1.0", name="ck_adj_events_step_factor_ge_1"),
        sa.CheckConstraint("event_type IN ('bonus', 'bonus_cash', 'right', 'unexplained_step')", name="ck_adj_events_event_type"),
        sa.CheckConstraint("method IN ('exchange_step_s4', 'ledger_formula', 'exchange_prev_close')", name="ck_adj_events_method"),
        sa.CheckConstraint("status IN ('verified', 'unverified', 'review_queue')", name="ck_adj_events_status"),
        sa.UniqueConstraint("symbol", "ex_date", name="uq_adj_events_symbol_ex_date"),
    )

    # 8. corporate_actions
    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("fiscal_year", sa.String(length=16), nullable=False),
        sa.Column("action_type", sa.String(length=16), nullable=False),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usable_from", sa.Date(), nullable=True),
        sa.Column("bookclose_date", sa.Date(), nullable=True),
        sa.Column("ex_date", sa.Date(), nullable=True),
        sa.Column("cash_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("bonus_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("right_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("right_ratio_num", sa.Integer(), nullable=True),
        sa.Column("right_ratio_den", sa.Integer(), nullable=True),
        sa.Column("right_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("document_ref", sa.String(), nullable=True),
        sa.Column("ex_date_status", sa.String(length=20), nullable=False, server_default="observed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action_type IN ('bonus', 'right', 'cash', 'combined')", name="ck_corporate_actions_action_type"),
        sa.CheckConstraint("ex_date_status IN ('observed', 'from_bookclose', 'pending')", name="ck_corporate_actions_ex_date_status"),
    )
    op.create_index("ix_corporate_actions_symbol_ex_date", "corporate_actions", ["symbol", "ex_date"])
    op.create_index("ix_corporate_actions_usable_from", "corporate_actions", ["usable_from"])

    # 9. index_daily
    op.create_table(
        "index_daily",
        sa.Column("index_name", sa.String(length=64), primary_key=True),
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("index_id", sa.Integer(), nullable=True),
        sa.Column("open", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("high", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("low", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("close", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("turnover", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("trades", sa.Integer(), nullable=True),
        sa.Column("percentage_change", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
    )

    # 10. sector_index_daily
    op.create_table(
        "sector_index_daily",
        sa.Column("index_name", sa.String(length=64), primary_key=True),
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("index_id", sa.Integer(), nullable=True),
        sa.Column("open", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("high", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("low", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("close", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("turnover", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("trades", sa.Integer(), nullable=True),
        sa.Column("percentage_change", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
    )

    # 11. quarterly_financials
    op.create_table(
        "quarterly_financials",
        sa.Column("symbol", sa.String(length=32), primary_key=True),
        sa.Column("fiscal_year", sa.String(length=16), primary_key=True),
        sa.Column("quarter", sa.SmallInteger(), primary_key=True),
        sa.Column("is_restated", sa.Boolean(), primary_key=True, server_default=sa.text("false")),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usable_from", sa.Date(), nullable=True),
        sa.Column("revenue", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("net_profit", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("eps_reported", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("eps_basis", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("eps_ytd", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("eps_annualized", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("eps_ttm", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("bvps", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("paid_up_capital", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("shares_outstanding_est", sa.BigInteger(), nullable=True),
        sa.Column("roe_annualized", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("pe_reported", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("npl_pct", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("unit_multiplier_applied", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("field_sources", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quarter BETWEEN 1 AND 4", name="ck_quarterly_financials_quarter_1_to_4"),
        sa.CheckConstraint("eps_basis IN ('annualized', 'ytd', 'quarter', 'unknown')", name="ck_quarterly_financials_eps_basis"),
    )
    op.create_index("ix_quarterly_financials_symbol_usable_from", "quarterly_financials", ["symbol", "usable_from"])

    # 12. valuation_daily
    op.create_table(
        "valuation_daily",
        sa.Column("symbol", sa.String(length=32), primary_key=True),
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("pe_pit", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("pe_ttm_pit", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("pb_pit", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("pe_reported", sa.Numeric(precision=12, scale=2), nullable=True),
    )

    # 13. floorsheet_daily_agg
    op.create_table(
        "floorsheet_daily_agg",
        sa.Column("symbol", sa.String(length=32), primary_key=True),
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("n_contracts", sa.Integer(), nullable=False),
        sa.Column("avg_contract_value", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("median_contract_value", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("block_share", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("small_lot_share", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("top5_buyer_share", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("top5_seller_share", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("buyer_hhi", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("seller_hhi", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("n_buyer_brokers", sa.Integer(), nullable=False),
        sa.Column("n_seller_brokers", sa.Integer(), nullable=False),
        sa.Column("bar_completeness", sa.Numeric(precision=6, scale=4), nullable=False),
    )
    op.create_index("ix_floorsheet_daily_agg_trade_date", "floorsheet_daily_agg", ["trade_date"])

    # 14. universe_membership
    op.create_table(
        "universe_membership",
        sa.Column("month_start", sa.Date(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), primary_key=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("median_turnover_250", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("trading_presence_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("in_universe", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_universe_membership_month_in_universe", "universe_membership", ["month_start", "in_universe"])

    # 15. snapshot_nepsepy_daily
    op.create_table(
        "snapshot_nepsepy_daily",
        sa.Column("symbol", sa.String(length=32), primary_key=True),
        sa.Column("snapshot_date", sa.Date(), primary_key=True),
        sa.Column("market_capitalization", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("fifty_two_week_high", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("fifty_two_week_low", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("last_updated_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("last_updated_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("average_traded_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("previous_day_close_price", sa.Numeric(precision=14, scale=2), nullable=True),
    )

    # 16. news_articles
    op.create_table(
        "news_articles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("excerpt", sa.String(length=600), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("sentiment_label", sa.String(length=16), nullable=True),
        sa.Column("sentiment_model", sa.String(length=64), nullable=True),
        sa.Column("embedding_id", sa.String(length=64), nullable=True),
        sa.Column("duplicate_of", sa.BigInteger(), sa.ForeignKey("news_articles.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("source IN ('sharesansar', 'bizmandu')", name="ck_news_articles_source"),
        sa.CheckConstraint("sentiment_score BETWEEN -1.0 AND 1.0", name="ck_news_articles_sentiment_score"),
        sa.CheckConstraint("sentiment_label IN ('positive', 'neutral', 'negative')", name="ck_news_articles_sentiment_label"),
    )
    op.create_index("ix_news_articles_published_at_desc", "news_articles", [sa.text("published_at DESC")])
    op.create_index("ix_news_articles_content_hash", "news_articles", ["content_hash"])
    op.create_index("ix_news_articles_unscored", "news_articles", ["id"], postgresql_where=sa.text("sentiment_score IS NULL"))

    # 17. news_symbols
    op.create_table(
        "news_symbols",
        sa.Column("article_id", sa.BigInteger(), sa.ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("security_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("match_method", sa.String(length=16), nullable=False, server_default="ticker"),
        sa.Column("relevance", sa.Float(), nullable=False, server_default="1.0"),
        sa.CheckConstraint("match_method IN ('ticker', 'name', 'manual')", name="ck_news_symbols_match_method"),
    )
    op.create_index("ix_news_symbols_security_id", "news_symbols", ["security_id"])

    # 18. jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('research', 'backtest', 'eod_prices', 'news_scrape', 'news_score', "
            "'fundamentals_import', 'signals_daily', 'weights_update', 'signals_backfill')",
            name="ck_jobs_kind"
        ),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name="ck_jobs_status"),
    )
    op.create_index("ix_jobs_status_created_at", "jobs", ["status", "created_at"])
    op.create_index("ix_jobs_kind_created_at_desc", "jobs", ["kind", sa.text("created_at DESC")])

    # 19. job_events
    op.create_table(
        "job_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("node", sa.String(length=32), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("job_id", "seq", name="uq_job_events_job_id_seq"),
    )

    # 20. agent_signals
    op.create_table(
        "agent_signals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("security_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("agent", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("drivers", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("risks", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("flags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("logic_version", sa.String(length=16), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("agent IN ('news', 'fundamentals', 'technicals', 'risk')", name="ck_agent_signals_agent"),
        sa.CheckConstraint("origin IN ('live', 'backfill')", name="ck_agent_signals_origin"),
        sa.UniqueConstraint("security_id", "as_of", "agent", "logic_version", "origin", name="uq_agent_signals_unique_key"),
    )
    op.create_index("ix_agent_signals_as_of", "agent_signals", ["as_of"])

    # 21. signal_outcomes
    op.create_table(
        "signal_outcomes",
        sa.Column("security_id", sa.Integer(), primary_key=True),
        sa.Column("as_of", sa.Date(), primary_key=True),
        sa.Column("agent", sa.String(length=16), primary_key=True),
        sa.Column("horizon_days", sa.SmallInteger(), primary_key=True),
        sa.Column("logic_version", sa.String(length=16), primary_key=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("forward_return", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("realized_on", sa.Date(), nullable=True),
        sa.Column("hit", sa.Boolean(), nullable=True),
        sa.CheckConstraint("agent IN ('news', 'fundamentals', 'technicals', 'consensus')", name="ck_signal_outcomes_agent"),
    )
    op.create_index("ix_signal_outcomes_agent_realized_on", "signal_outcomes", ["agent", "realized_on"])

    # 22. research_briefs
    op.create_table(
        "research_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("security_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("label", sa.String(length=8), nullable=True),
        sa.Column("consensus_score", sa.Float(), nullable=True),
        sa.Column("raw_confidence", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("position_multiplier", sa.Float(), nullable=True),
        sa.Column("conflicted", sa.Boolean(), nullable=True),
        sa.Column("brief", postgresql.JSONB(), nullable=False),
        sa.Column("used_llm", sa.Boolean(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("label IN ('BUY', 'HOLD', 'SELL')", name="ck_research_briefs_label"),
    )
    op.create_index("ix_research_briefs_security_as_of_created", "research_briefs", ["security_id", sa.text("as_of DESC"), sa.text("created_at DESC")])
    op.create_index("ix_research_briefs_created_at_desc", "research_briefs", [sa.text("created_at DESC")])

    # 23. agent_weights
    op.create_table(
        "agent_weights",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("fitted_on", sa.Date(), nullable=False),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.Column("calibrator", postgresql.JSONB(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_weights_scope_fitted_on_desc", "agent_weights", ["scope", sa.text("fitted_on DESC")])

    # 24. backtest_runs
    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="ck_backtest_runs_status"),
    )

    # 25. backtest_strategy_results
    op.create_table(
        "backtest_strategy_results",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("strategy_key", sa.String(length=64), primary_key=True),
        sa.Column("is_benchmark", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("bootstrap", postgresql.JSONB(), nullable=True),
    )

    # 26. backtest_equity
    op.create_table(
        "backtest_equity",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("strategy_key", sa.String(length=64), primary_key=True),
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("equity", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("drawdown", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("exposure", sa.Numeric(precision=8, scale=4), nullable=False),
    )

    # 27. backtest_trades
    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("strategy_key", sa.String(length=64), nullable=False),
        sa.Column("security_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("exit_date", sa.Date(), nullable=True),
        sa.Column("entry_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("exit_price", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("gross_pnl", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("costs", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.0"),
        sa.Column("tax", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0.0"),
        sa.Column("net_pnl", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("return_pct", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("holding_days", sa.Integer(), nullable=True),
        sa.Column("exit_reason", sa.String(length=32), nullable=True),
        sa.CheckConstraint("exit_reason IN ('signal', 'end_of_test', 'delisted', 'stop_loss')", name="ck_backtest_trades_exit_reason"),
    )
    op.create_index("ix_backtest_trades_run_id_strategy_key", "backtest_trades", ["run_id", "strategy_key"])

    # 28. backtest_folds
    op.create_table(
        "backtest_folds",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("fold_idx", sa.Integer(), primary_key=True),
        sa.Column("train_start", sa.Date(), nullable=False),
        sa.Column("train_end", sa.Date(), nullable=False),
        sa.Column("test_start", sa.Date(), nullable=False),
        sa.Column("test_end", sa.Date(), nullable=False),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.Column("calibrator", postgresql.JSONB(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
    )

    # 29. ingestion_runs
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_loaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint("status IN ('running', 'succeeded', 'failed', 'partial')", name="ck_ingestion_runs_status"),
    )

    # 30. uploads
    op.create_table(
        "uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("upload_type", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="validated"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("staged_path", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("upload_type IN ('prices_csv', 'fundamentals_csv')", name="ck_uploads_upload_type"),
        sa.CheckConstraint("status IN ('validated', 'rejected', 'committed')", name="ck_uploads_status"),
    )

    # 31. llm_cache
    op.create_table(
        "llm_cache",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_llm_cache_created_at", "llm_cache", ["created_at"])


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS daily_prices CASCADE;")
    tables = [
        "llm_cache", "uploads", "ingestion_runs", "backtest_folds", "backtest_trades",
        "backtest_equity", "backtest_strategy_results", "backtest_runs", "agent_weights",
        "research_briefs", "signal_outcomes", "agent_signals", "job_events", "jobs",
        "news_symbols", "news_articles", "snapshot_nepsepy_daily", "universe_membership",
        "floorsheet_daily_agg", "valuation_daily", "quarterly_financials", "sector_index_daily",
        "index_daily", "corporate_actions", "adj_events", "daily_bars", "dim_trading_day",
        "symbol_alias", "securities", "api_keys", "users"
    ]
    for t in tables:
        op.drop_table(t, if_exists=True)
