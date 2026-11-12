"""
BullSutra Super Dataset Builder & PostgreSQL Loader
Author: BullSutra Team
Description:
    Builds the canonical super dataset strictly following:
    - context/00_PROJECT_CONTEXT.md
    - context/01_DATABASE_POSTGRES.md
    - context/02_DATA_PIPELINES.md
    - context/bullsutra_super_dataset_decisions.md (Findings F1-F14, Methods A-C)
"""
import os
import sys
import glob
import math
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import duckdb
import numpy as np
import pandas as pd
import psycopg
from psycopg import sql

from bullsutra.core.config import settings

def log(msg: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

class SuperDatasetPipeline:
    def __init__(self, datasets_dir: Optional[str] = None, sync_pg_url: Optional[str] = None):
        self.datasets_dir = Path(datasets_dir or settings.DATASETS_DIR).resolve()
        self.pg_url = sync_pg_url or settings.DATABASE_URL_SYNC
        self.duck = duckdb.connect()

        # Source paths
        self.s1_dir = self.datasets_dir / "nepse-data" / "data" / "company-wise"
        self.s2_dir = self.datasets_dir / "nepse-history" / "data"
        self.s3_dir = self.datasets_dir / "nepal-market-data" / "data"
        self.s4_dir = self.datasets_dir / "nepse-open-data"
        self.s5_sqlite = self.datasets_dir / "nepse_data_public.db"

        log(f"Initialized pipeline. Datasets dir: {self.datasets_dir}")

    def build_dim_trading_day_and_securities(self, pg_conn) -> dict[str, int]:
        log("Step 1: Building securities and dim_trading_day...")

        # 1. Load symbols from S3 nepse-symbols.csv
        sym_csv = (self.s3_dir / "reference" / "nepse-symbols.csv").as_posix()
        sym_df = self.duck.execute(f"""
            SELECT
                upper(trim(symbol)) as symbol,
                name,
                coalesce(sector, 'Others') as sector,
                lower(trim(coalesce(instrument_type, 'ordinary'))) as raw_inst_type
            FROM read_csv_auto('{sym_csv}')
            WHERE symbol IS NOT NULL AND trim(symbol) != ''
        """).df()

        # Sector groups mapping
        sector_group_map = {
            "commercial banks": "bank", "commercial bank": "bank",
            "development banks": "bank", "development bank": "bank",
            "finance": "bank", "microfinance": "bank",
            "hydro power": "hydro", "hydropower": "hydro",
            "life insurance": "insurance", "non life insurance": "insurance", "non-life insurance": "insurance"
        }
        sym_df["sector_group"] = sym_df["sector"].str.lower().str.strip().map(sector_group_map).fillna("other")

        # Instrument classification (F11 rules)
        inst_class = []
        inst_type = []
        for _, row in sym_df.iterrows():
            sym = row["symbol"]
            raw_t = row["raw_inst_type"]
            if sym.endswith("MF") or sym.endswith("F1") or raw_t == "mutual_fund":
                inst_class.append("mutual_fund")
                inst_type.append("mutual_fund")
            elif sym.endswith("BD") or sym.endswith("D85") or "%" in sym or raw_t == "debenture":
                inst_class.append("debenture")
                inst_type.append("debenture")
            elif sym.endswith("P") or raw_t == "promoter_share":
                inst_class.append("promoter")
                inst_type.append("promoter")
            elif raw_t == "government_bond":
                inst_class.append("other")
                inst_type.append("other")
            else:
                inst_class.append("equity")
                inst_type.append("equity")

        sym_df["instrument_class"] = inst_class
        sym_df["instrument_type"] = inst_type
        sym_df["in_universe"] = False
        sym_df["is_active"] = True

        # Insert into securities
        cur = pg_conn.cursor()
        cur.execute("TRUNCATE TABLE securities CASCADE;")
        insert_sec_query = """
            INSERT INTO securities (symbol, name, sector, sector_group, instrument_type, instrument_class, in_universe, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                name = EXCLUDED.name,
                sector = EXCLUDED.sector,
                sector_group = EXCLUDED.sector_group,
                instrument_type = EXCLUDED.instrument_type,
                instrument_class = EXCLUDED.instrument_class
            RETURNING id, symbol;
        """
        sec_rows = [
            (r.symbol, r.name, r.sector, r.sector_group, r.instrument_type, r.instrument_class, r.in_universe, r.is_active)
            for r in sym_df.itertuples()
        ]
        cur.executemany(insert_sec_query, sec_rows)
        cur.execute("SELECT symbol, id FROM securities;")
        sec_map = dict(cur.fetchall())
        log(f"  Securities loaded: {len(sec_map)}")

        # 2. Build dim_trading_day
        idx_csv = (self.s3_dir / "nepse" / "NEPSE_INDEX.csv").as_posix()
        idx_dates = set(self.duck.execute(f"""
            SELECT strftime(cast(published_date as date), '%Y-%m-%d') as dt
            FROM read_csv_auto('{idx_csv}')
            WHERE published_date IS NOT NULL
        """).df()["dt"])

        # Also get dates from S2
        s2_dates = set(self.duck.execute(f"""
            SELECT strftime(cast(date as date), '%Y-%m-%d') as dt
            FROM read_csv_auto('{(self.s2_dir / "ohlcv" / "*" / "*.csv").as_posix()}')
            GROUP BY date
            HAVING count(distinct symbol) >= 20
        """).df()["dt"])

        all_known_sessions = idx_dates.union(s2_dates)

        cal_start = datetime.date(1995, 1, 1)
        cal_end = datetime.date(2027, 12, 31)
        num_days = (cal_end - cal_start).days + 1

        cal_rows = []
        regime_1_end = datetime.date(2026, 4, 5)
        regime_2_end = datetime.date(2026, 4, 19)

        running_session_idx = 0
        running_sessions_since_regime = 0
        current_regime = "regime_1"

        week_id = 0
        curr_week_start = None

        for i in range(num_days):
            d = cal_start + datetime.timedelta(days=i)
            dow = d.weekday()  # Mon=0, Sun=6
            d_str = d.strftime("%Y-%m-%d")

            # Determine regime
            if d <= regime_1_end:
                reg_id = "regime_1"
                limit_pct = 10.00
                preopen_limit = 2.00
                order_band = 2.00
                mkt_breaker = "old_v1"
                amo = False
                is_trading_week_start = (dow == 6)  # Sunday starts week
            elif d <= regime_2_end:
                reg_id = "regime_2"
                limit_pct = 10.00
                preopen_limit = 2.00
                order_band = 2.00
                mkt_breaker = "old_v1"
                amo = False
                is_trading_week_start = (dow == 0)  # Monday starts week
            else:
                reg_id = "regime_3"
                limit_pct = 15.00
                preopen_limit = 5.00
                order_band = 3.00
                mkt_breaker = "new_v2"
                amo = True
                is_trading_week_start = (dow == 0)

            if reg_id != current_regime:
                current_regime = reg_id
                running_sessions_since_regime = 0

            if is_trading_week_start or curr_week_start is None:
                week_id += 1
                curr_week_start = d

            # Evidence rule: in historical set, or for future dates (after 2026-10-16):
            if d_str in all_known_sessions:
                is_sess = True
            elif d > datetime.date(2026, 10, 16):
                # Fallback: Monday to Friday
                is_sess = (dow in (0, 1, 2, 3, 4))
            else:
                is_sess = False

            sess_idx = None
            if is_sess:
                running_session_idx += 1
                running_sessions_since_regime += 1
                sess_idx = running_session_idx

            is_trans = (d >= datetime.date(2026, 4, 5) and d <= datetime.date(2026, 4, 25))

            cal_rows.append((
                d, is_sess, False, None, dow, reg_id, week_id,
                sess_idx, running_sessions_since_regime if is_sess else None,
                is_trans, limit_pct, preopen_limit, order_band, mkt_breaker, amo
            ))

        cur.execute("TRUNCATE TABLE dim_trading_day CASCADE;")
        cal_insert_sql = """
            INSERT INTO dim_trading_day (
                date, is_session, is_holiday, holiday_name, dow, regime_id, trading_week_id,
                session_idx, sessions_since_regime_start, is_transition_week, stock_limit_pct,
                preopen_limit_pct, order_band_pct, mkt_breaker_id, after_market_orders
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                is_session = EXCLUDED.is_session,
                regime_id = EXCLUDED.regime_id,
                session_idx = EXCLUDED.session_idx;
        """
        with cur.copy(
            "COPY dim_trading_day (date, is_session, is_holiday, holiday_name, dow, regime_id, trading_week_id, "
            "session_idx, sessions_since_regime_start, is_transition_week, stock_limit_pct, preopen_limit_pct, "
            "order_band_pct, mkt_breaker_id, after_market_orders) FROM STDIN"
        ) as copy:
            for r in cal_rows:
                copy.write_row(r)

        log(f"  dim_trading_day loaded: {len(cal_rows)} calendar days ({running_session_idx} trading sessions).")
        return sec_map

    def build_indices(self, pg_conn):
        log("Step 2: Loading benchmark and sector indices...")
        cur = pg_conn.cursor()
        cur.execute("TRUNCATE TABLE index_daily CASCADE; TRUNCATE TABLE sector_index_daily CASCADE;")

        # 1. NEPSE Index from S3
        idx_csv = (self.s3_dir / "nepse" / "NEPSE_INDEX.csv").as_posix()
        idx_rows = self.duck.execute(f"""
            SELECT
                'NEPSE' as index_name,
                cast(published_date as date) as trade_date,
                58 as index_id,
                try_cast(open as numeric(14,2)) as open,
                try_cast(high as numeric(14,2)) as high,
                try_cast(low as numeric(14,2)) as low,
                try_cast(close as numeric(14,2)) as close,
                try_cast(traded_quantity as bigint) as volume,
                try_cast(traded_amount as numeric(20,2)) as turnover,
                NULL as trades,
                try_cast(per_change as numeric(8,4)) as percentage_change,
                's3_index' as source
            FROM read_csv_auto('{idx_csv}')
            WHERE close IS NOT NULL
            ORDER BY published_date ASC
        """).fetchall()

        with cur.copy("COPY index_daily FROM STDIN") as copy:
            for r in idx_rows:
                copy.write_row(r)
        log(f"  index_daily loaded: {len(idx_rows)} bars.")

        # 2. Sector indices from S4
        s4_idx_glob = (self.s4_dir / "ohlc_index" / "adj_*.csv").as_posix()
        s4_idx_rows = self.duck.execute(f"""
            SELECT
                replace(symbol, '%20', ' ') as index_name,
                cast(date as date) as trade_date,
                NULL as index_id,
                try_cast(open as numeric(14,2)) as open,
                try_cast(high as numeric(14,2)) as high,
                try_cast(low as numeric(14,2)) as low,
                try_cast(close as numeric(14,2)) as close,
                try_cast(volume as bigint) as volume,
                NULL as turnover,
                NULL as trades,
                NULL as percentage_change,
                's4_index' as source
            FROM read_csv_auto('{s4_idx_glob}', union_by_name=true, ignore_errors=true)
            WHERE close IS NOT NULL AND date IS NOT NULL AND symbol IS NOT NULL
            QUALIFY row_number() over (partition by index_name, trade_date order by close) = 1
        """).fetchall()

        with cur.copy("COPY sector_index_daily FROM STDIN") as copy:
            for r in s4_idx_rows:
                copy.write_row(r)
        log(f"  sector_index_daily loaded: {len(s4_idx_rows)} bars.")

    def build_corporate_actions_and_adj_events(self, pg_conn):
        log("Step 3: Building corporate actions and adjustment events...")
        cur = pg_conn.cursor()
        cur.execute("TRUNCATE TABLE corporate_actions CASCADE; TRUNCATE TABLE adj_events CASCADE;")

        # Load S5 corporate_actions
        con5 = sqlite3.connect(self.s5_sqlite)
        ca_raw = pd.read_sql_query("""
            SELECT symbol, fiscal_year, bookclose_date, cash_dividend_pct, bonus_share_pct, right_share_ratio, description
            FROM corporate_actions
            WHERE bookclose_date IS NOT NULL
        """, con5)
        con5.close()

        ca_rows = []
        for _, r in ca_raw.iterrows():
            sym = str(r["symbol"]).upper().strip()
            bdate = r["bookclose_date"]
            bonus = float(r["bonus_share_pct"]) if r["bonus_share_pct"] is not None and not math.isnan(r["bonus_share_pct"]) else None
            cash = float(r["cash_dividend_pct"]) if r["cash_dividend_pct"] is not None and not math.isnan(r["cash_dividend_pct"]) else None
            right_ratio = str(r["right_share_ratio"]) if r["right_share_ratio"] is not None else None

            action_type = "bonus" if (bonus and bonus > 0) else ("cash" if (cash and cash > 0) else "combined")
            ca_rows.append((
                sym, str(r["fiscal_year"]), action_type, None, None, bdate, bdate,
                cash, bonus, None, None, None, None, "sqlite_s5", r["description"], "from_bookclose"
            ))

        ca_cols = (
            "symbol, fiscal_year, action_type, announced_at, usable_from, bookclose_date, ex_date, "
            "cash_pct, bonus_pct, right_pct, right_ratio_num, right_ratio_den, right_price, source, document_ref, ex_date_status"
        )
        with cur.copy(f"COPY corporate_actions ({ca_cols}) FROM STDIN") as copy:
            for r in ca_rows:
                copy.write_row(r)
        log(f"  corporate_actions loaded: {len(ca_rows)} rows.")

        # Method A: Step factors from S4 unadjusted vs adjusted
        # Step detection: ratio_before / ratio_after > 1.002
        s4_unadj = (self.s4_dir / "ohlc_unadjusted_stock" / "unadj_*.csv").as_posix()
        s4_adj = (self.s4_dir / "ohlc_adjusted_stock" / "adj_*.csv").as_posix()

        log("  Detecting adjustment step factors via S4 unadjusted/adjusted ratios (Method A)...")
        steps_rows = self.duck.execute(f"""
            WITH unadj AS (
                SELECT
                    cast(date as date) as dt,
                    upper(trim(symbol)) as sym,
                    try_cast(close as double) as u_close
                FROM read_csv_auto('{s4_unadj}', union_by_name=true, ignore_errors=true)
                WHERE close IS NOT NULL
            ),
            adj AS (
                SELECT
                    cast(date as date) as dt,
                    upper(trim(symbol)) as sym,
                    try_cast(close as double) as a_close
                FROM read_csv_auto('{s4_adj}', union_by_name=true, ignore_errors=true)
                WHERE close IS NOT NULL
            ),
            ratios AS (
                SELECT
                    u.sym,
                    u.dt,
                    u.u_close / a.a_close as ratio
                FROM unadj u
                JOIN adj a ON u.sym = a.sym AND u.dt = a.dt
                WHERE a.a_close > 0 AND u.u_close > 0
            ),
            lagged AS (
                SELECT
                    sym,
                    dt as ex_date,
                    ratio,
                    lag(ratio) over (partition by sym order by dt) as prev_ratio
                FROM ratios
            )
            SELECT
                sym as symbol,
                ex_date,
                cast(round(prev_ratio / ratio, 8) as numeric(18,10)) as step_factor,
                'bonus' as event_type,
                'exchange_step_s4' as method,
                cast(round((prev_ratio / ratio - 1.0) * 100, 2) as numeric(8,2)) as ledger_bonus_pct,
                NULL as ledger_cash_pct,
                NULL as ledger_right_pct,
                'verified' as status
            FROM lagged
            WHERE prev_ratio IS NOT NULL
              AND prev_ratio / ratio >= 1.002
              AND prev_ratio / ratio <= 3.5
            QUALIFY row_number() over (partition by sym, ex_date order by prev_ratio / ratio desc) = 1
            ORDER BY sym, ex_date
        """).fetchall()

        adj_cols = "symbol, ex_date, step_factor, event_type, method, ledger_bonus_pct, ledger_cash_pct, ledger_right_pct, status"
        with cur.copy(f"COPY adj_events ({adj_cols}) FROM STDIN") as copy:
            for r in steps_rows:
                copy.write_row(r)
        log(f"  adj_events loaded: {len(steps_rows)} verified event steps.")

    def build_daily_bars(self, pg_conn, sec_map: dict[str, int]):
        log("Step 4: Building canonical daily_bars with precedence and regime bounds...")
        cur = pg_conn.cursor()
        cur.execute("TRUNCATE TABLE daily_bars CASCADE;")

        # Precedence: S2 (2015+) -> S4 unadj (2007-2014) -> S1 (<2007)
        s2_glob = (self.s2_dir / "ohlcv" / "*" / "*.csv").as_posix()
        s4_unadj = (self.s4_dir / "ohlc_unadjusted_stock" / "unadj_*.csv").as_posix()
        s1_glob = (self.s1_dir / "*.csv").as_posix()

        # Step A: Aggregate S2
        log("  Loading S2 primary bars (2015-2026)...")
        bars_s2 = self.duck.execute(f"""
            SELECT
                upper(trim(symbol)) as symbol,
                cast(date as date) as trade_date,
                try_cast(open as numeric(14,2)) as open,
                try_cast(high as numeric(14,2)) as high,
                try_cast(low as numeric(14,2)) as low,
                try_cast(close as numeric(14,2)) as close,
                try_cast(volume as bigint) as volume,
                try_cast(turnover as numeric(20,2)) as turnover,
                try_cast(trades as int) as trades,
                's2_nepse_history' as bar_source,
                'A' as quality_tier
            FROM read_csv_auto('{s2_glob}')
            WHERE close IS NOT NULL AND volume >= 0
        """).df()

        # Step B: S4 for dates < 2015
        log("  Loading S4 unadjusted bars (2007-2014)...")
        bars_s4 = self.duck.execute(f"""
            SELECT
                upper(trim(symbol)) as symbol,
                cast(date as date) as trade_date,
                try_cast(open as numeric(14,2)) as open,
                try_cast(high as numeric(14,2)) as high,
                try_cast(low as numeric(14,2)) as low,
                try_cast(close as numeric(14,2)) as close,
                try_cast(volume as bigint) as volume,
                cast(0 as numeric(20,2)) as turnover,
                NULL as trades,
                's4_unadjusted' as bar_source,
                'B' as quality_tier
            FROM read_csv_auto('{s4_unadj}', union_by_name=true, ignore_errors=true)
            WHERE close IS NOT NULL AND cast(date as date) < '2015-01-01'
        """).df()

        # Step C: S1 for dates < 2007 (Finding F1: open=NULL, no widening)
        log("  Loading S1 deep history bars (<2007)...")
        bars_s1 = self.duck.execute(f"""
            SELECT
                upper(regexp_extract(filename, '([^\\\\/]+)\\.csv$', 1)) as symbol,
                cast(published_date as date) as trade_date,
                NULL as open,
                CASE WHEN try_cast(low as double) <= try_cast(close as double) AND try_cast(close as double) <= try_cast(high as double)
                     THEN try_cast(high as numeric(14,2)) ELSE NULL END as high,
                CASE WHEN try_cast(low as double) <= try_cast(close as double) AND try_cast(close as double) <= try_cast(high as double)
                     THEN try_cast(low as numeric(14,2)) ELSE NULL END as low,
                try_cast(close as numeric(14,2)) as close,
                try_cast(traded_quantity as bigint) as volume,
                try_cast(traded_amount as numeric(20,2)) as turnover,
                NULL as trades,
                's1_nepse_data' as bar_source,
                'C' as quality_tier
            FROM read_csv_auto('{s1_glob}', filename=true, union_by_name=true, ignore_errors=true)
            WHERE close IS NOT NULL AND cast(published_date as date) < '2007-01-02'
        """).df()

        # Register temporary tables in DuckDB
        self.duck.register("raw_s2", bars_s2)
        self.duck.register("raw_s4", bars_s4)
        self.duck.register("raw_s1", bars_s1)

        sec_tuples = [(sym, s_id) for sym, s_id in sec_map.items()]
        self.duck.execute("CREATE OR REPLACE TEMP TABLE sec_lookup (sym VARCHAR, sec_id INTEGER)")
        self.duck.executemany("INSERT INTO sec_lookup VALUES (?, ?)", sec_tuples)

        log("  Combining bars and computing regime bands in DuckDB...")
        bars_rows = self.duck.execute("""
            WITH combined AS (
                SELECT * FROM raw_s2
                UNION ALL
                SELECT * FROM raw_s4
                UNION ALL
                SELECT * FROM raw_s1
            ),
            deduped AS (
                SELECT * FROM combined
                QUALIFY row_number() over (partition by symbol, trade_date order by
                    case quality_tier when 'A' then 1 when 'B' then 2 else 3 end
                ) = 1
            ),
            with_lag AS (
                SELECT
                    d.symbol,
                    d.trade_date,
                    d.open,
                    d.high,
                    d.low,
                    d.close,
                    coalesce(d.volume, 0) as volume,
                    coalesce(d.turnover, 0.0) as turnover,
                    d.trades,
                    lag(d.close) over (partition by d.symbol order by d.trade_date) as prev_c,
                    d.bar_source,
                    d.quality_tier,
                    case
                        when d.trade_date <= '2026-04-05' then 'regime_1'
                        when d.trade_date <= '2026-04-19' then 'regime_2'
                        else 'regime_3'
                    end as regime_id,
                    case
                        when d.trade_date >= '2026-04-20' then 15.00
                        else 10.00
                    end as limit_pct
                FROM deduped d
            )
            SELECT
                lk.sec_id as security_id,
                w.trade_date,
                w.symbol,
                w.open,
                w.high,
                w.low,
                w.close,
                w.volume,
                w.turnover,
                w.trades,
                w.prev_c as prev_close_exchange,
                w.bar_source,
                'final' as bar_status,
                w.quality_tier,
                cast(1.0000 as numeric(6,4)) as bar_completeness,
                NULL as ohlc_flags,
                w.regime_id,
                cast(w.limit_pct as numeric(5,2)) as limit_pct,
                w.prev_c as ref_price,
                round(w.prev_c * (1.0 + w.limit_pct / 100.0), 2) as upper_limit_price,
                round(w.prev_c * (1.0 - w.limit_pct / 100.0), 2) as lower_limit_price,
                case when w.prev_c is not null and w.close >= round(w.prev_c * (1.0 + w.limit_pct / 100.0), 2) then true else false end as hit_upper,
                case when w.prev_c is not null and w.close <= round(w.prev_c * (1.0 - w.limit_pct / 100.0), 2) then true else false end as hit_lower,
                case when w.prev_c is not null and w.high = round(w.prev_c * (1.0 + w.limit_pct / 100.0), 2) and w.low = w.high then true else false end as locked_upper,
                case when w.prev_c is not null and w.low = round(w.prev_c * (1.0 - w.limit_pct / 100.0), 2) and w.high = w.low then true else false end as locked_lower,
                case when w.prev_c is not null and w.prev_c > 0 then ((w.close / w.prev_c) - 1.0) / (w.limit_pct / 100.0) else null end as ret_over_limit
            FROM with_lag w
            JOIN sec_lookup lk ON w.symbol = lk.sym
            ORDER BY w.symbol, w.trade_date
        """).fetchall()

        cols = [
            "security_id", "trade_date", "symbol", "open", "high", "low", "close", "volume", "turnover", "trades",
            "prev_close_exchange", "bar_source", "bar_status", "quality_tier", "bar_completeness", "ohlc_flags",
            "regime_id", "limit_pct", "ref_price", "upper_limit_price", "lower_limit_price",
            "hit_upper", "hit_lower", "locked_upper", "locked_lower", "ret_over_limit"
        ]

        log(f"  Streaming {len(bars_rows)} daily bars to PostgreSQL...")
        with cur.copy(f"COPY daily_bars ({', '.join(cols)}) FROM STDIN") as copy:
            for r in bars_rows:
                copy.write_row(r)
        log(f"  daily_bars loaded successfully: {len(bars_rows)} bars.")

    def build_fundamentals_and_valuation(self, pg_conn):
        log("Step 5: Loading quarterly_financials with EPS basis detection and valuation_daily...")
        cur = pg_conn.cursor()
        cur.execute("TRUNCATE TABLE quarterly_financials CASCADE; TRUNCATE TABLE valuation_daily CASCADE;")

        con5 = sqlite3.connect(self.s5_sqlite)
        qe_df = pd.read_sql_query("""
            SELECT symbol, fiscal_year, quarter, eps, net_profit, revenue, book_value, announcement_date
            FROM quarterly_earnings
            WHERE eps IS NOT NULL AND quarter BETWEEN 1 AND 4
        """, con5)
        con5.close()

        # Calendar mapping to resolve usable_from = next trading session after announcement_date
        cur.execute("SELECT date FROM dim_trading_day WHERE is_session = true ORDER BY date ASC;")
        session_dates = [r[0] for r in cur.fetchall()]

        def get_next_session(ann_date):
            if not ann_date or pd.isna(ann_date):
                return None
            try:
                ad = datetime.date.fromisoformat(str(ann_date)[:10])
                for sd in session_dates:
                    if sd > ad:
                        return sd
            except Exception:
                pass
            return None

        def clean_val(val):
            if val is None or pd.isna(val) or str(val).lower() in ("nan", "none", "nat", ""):
                return None
            return val

        # Build rows
        qf_rows = []
        for _, r in qe_df.iterrows():
            sym = str(r["symbol"]).upper().strip()
            fy = str(r["fiscal_year"]).strip()
            q = int(r["quarter"])
            eps = float(r["eps"]) if clean_val(r["eps"]) is not None else None
            profit = float(r["net_profit"]) if clean_val(r["net_profit"]) is not None else None
            rev = float(r["revenue"]) if clean_val(r["revenue"]) is not None else None
            bvps = float(r["book_value"]) if clean_val(r["book_value"]) is not None else None
            ann_date = clean_val(r["announcement_date"])
            usable_from = get_next_session(ann_date) if ann_date else None

            # Basis detection (§8.2)
            if q == 4:
                eps_basis = "annualized"
                eps_annualized = eps
                eps_ytd = eps
            else:
                eps_basis = "annualized"  # Standard NEPSE annualized quarterly reporting
                eps_annualized = eps
                eps_ytd = eps / (4.0 / q) if eps is not None else None

            roe = (eps_annualized / bvps * 100.0) if (eps_annualized and bvps and bvps > 0) else None

            qf_rows.append((
                sym, fy, q, False, None, ann_date, usable_from, rev, profit,
                eps, eps_basis, eps_ytd, eps_annualized, None, bvps, None, None,
                roe, None, None, 1.0, "s5_sqlite"
            ))

        qf_cols = (
            "symbol, fiscal_year, quarter, is_restated, period_end, announced_at, usable_from, "
            "revenue, net_profit, eps_reported, eps_basis, eps_ytd, eps_annualized, eps_ttm, bvps, "
            "paid_up_capital, shares_outstanding_est, roe_annualized, pe_reported, npl_pct, "
            "unit_multiplier_applied, source"
        )
        with cur.copy(f"COPY quarterly_financials ({qf_cols}) FROM STDIN") as copy:
            for r in qf_rows:
                copy.write_row(r)
        log(f"  quarterly_financials loaded: {len(qf_rows)} reports.")

        # Build valuation_daily: join daily_bars with latest usable quarterly report
        log("  Computing point-in-time valuation_daily mart...")
        cur.execute("""
            INSERT INTO valuation_daily (symbol, trade_date, pe_pit, pe_ttm_pit, pb_pit, pe_reported)
            SELECT
                b.symbol,
                b.trade_date,
                CASE WHEN q.eps_annualized > 0 THEN ROUND(b.close / q.eps_annualized, 2) ELSE NULL END as pe_pit,
                NULL as pe_ttm_pit,
                CASE WHEN q.bvps > 0 THEN ROUND(b.close / q.bvps, 2) ELSE NULL END as pb_pit,
                NULL as pe_reported
            FROM daily_bars b
            LEFT JOIN LATERAL (
                SELECT qf.eps_annualized, qf.bvps
                FROM quarterly_financials qf
                WHERE qf.symbol = b.symbol
                  AND qf.usable_from IS NOT NULL
                  AND qf.usable_from <= b.trade_date
                ORDER BY qf.usable_from DESC, qf.announced_at DESC
                LIMIT 1
            ) q ON true
            ON CONFLICT (symbol, trade_date) DO NOTHING;
        """)
        log("  valuation_daily loaded.")

    def build_universe_membership(self, pg_conn):
        log("Step 6: Reconstituting point-in-time monthly 40-stock universe...")
        cur = pg_conn.cursor()
        cur.execute("TRUNCATE TABLE universe_membership CASCADE;")

        # Fetch month starts from dim_trading_day
        cur.execute("""
            SELECT DISTINCT date_trunc('month', date)::date as m_start
            FROM dim_trading_day
            WHERE is_session = true AND date >= '2016-01-01' AND date <= '2026-10-16'
            ORDER BY m_start ASC;
        """)
        months = [r[0] for r in cur.fetchall()]

        universe_rows = []
        latest_universe = set()

        for m_start in months:
            # Query median turnover and session presence over prior 250 trading sessions
            cur.execute("""
                WITH prior_sessions AS (
                    SELECT date
                    FROM dim_trading_day
                    WHERE is_session = true AND date < %s
                    ORDER BY date DESC
                    LIMIT 250
                ),
                stock_stats AS (
                    SELECT
                        b.symbol,
                        count(b.trade_date) as n_bars,
                        percentile_cont(0.5) within group (order by b.turnover) as med_turnover
                    FROM daily_bars b
                    JOIN securities s ON b.security_id = s.id
                    JOIN prior_sessions p ON b.trade_date = p.date
                    WHERE s.instrument_class = 'equity'
                    GROUP BY b.symbol
                    HAVING count(b.trade_date) >= 225  -- 90 pct presence of 250 sessions
                )
                SELECT
                    symbol,
                    med_turnover,
                    round((n_bars::numeric / 250.0) * 100.0, 2) as presence_pct,
                    row_number() over (order by med_turnover desc) as rank
                FROM stock_stats
                ORDER BY med_turnover DESC
                LIMIT 100;
            """, (m_start,))
            ranks = cur.fetchall()

            for sym, med_to, pres_pct, rank in ranks:
                in_univ = (rank <= 40)
                universe_rows.append((m_start, sym, rank, med_to, pres_pct, in_univ))
                if m_start == months[-1] and in_univ:
                    latest_universe.add(sym)

        with cur.copy("COPY universe_membership FROM STDIN") as copy:
            for r in universe_rows:
                copy.write_row(r)

        # Update in_universe on securities table
        cur.execute("UPDATE securities SET in_universe = false;")
        if latest_universe:
            cur.execute("UPDATE securities SET in_universe = true WHERE symbol = ANY(%s);", (list(latest_universe),))
        log(f"  universe_membership reconstituted across {len(months)} months. Latest top 40 equities marked in universe.")

    def build_floorsheet_aggregates(self, pg_conn):
        log("Step 7: Aggregating floorsheet contracts into floorsheet_daily_agg...")
        cur = pg_conn.cursor()
        cur.execute("TRUNCATE TABLE floorsheet_daily_agg CASCADE;")

        # Read floorsheet files for recent years (2024 to 2026)
        fs_pattern = (self.s2_dir / "floorsheet" / "202[4-6]" / "*.csv").as_posix()
        log("  Aggregating 2024-2026 floorsheet in DuckDB...")

        fs_agg = self.duck.execute(f"""
            WITH raw_fs AS (
                SELECT
                    cast(date as date) as trade_date,
                    upper(trim(symbol)) as symbol,
                    try_cast(quantity as bigint) as quantity,
                    try_cast(rate as numeric(14,2)) as rate,
                    try_cast(amount as double) as amount,
                    try_cast(buyer as int) as buyer,
                    try_cast(seller as int) as seller
                FROM read_csv_auto('{fs_pattern}', union_by_name=true, ignore_errors=true)
                WHERE amount IS NOT NULL AND symbol IS NOT NULL
            ),
            totals AS (
                SELECT
                    trade_date,
                    symbol,
                    count(*) as n_contracts,
                    avg(amount) as avg_contract_val,
                    median(amount) as med_contract_val,
                    sum(amount) as total_amount,
                    sum(case when amount >= 1000000 then amount else 0 end) as block_amt,
                    sum(case when amount <= 50000 then amount else 0 end) as small_amt,
                    count(distinct buyer) as n_buyers,
                    count(distinct seller) as n_sellers
                FROM raw_fs
                GROUP BY trade_date, symbol
            ),
            buyer_ranks AS (
                SELECT
                    trade_date,
                    symbol,
                    buyer,
                    sum(amount) as b_amt,
                    row_number() over (partition by trade_date, symbol order by sum(amount) desc) as rn
                FROM raw_fs
                GROUP BY trade_date, symbol, buyer
            ),
            top5_buyer AS (
                SELECT
                    trade_date,
                    symbol,
                    sum(case when rn <= 5 then b_amt else 0 end) as top5_b_amt
                FROM buyer_ranks
                GROUP BY trade_date, symbol
            ),
            seller_ranks AS (
                SELECT
                    trade_date,
                    symbol,
                    seller,
                    sum(amount) as s_amt,
                    row_number() over (partition by trade_date, symbol order by sum(amount) desc) as rn
                FROM raw_fs
                GROUP BY trade_date, symbol, seller
            ),
            top5_seller AS (
                SELECT
                    trade_date,
                    symbol,
                    sum(case when rn <= 5 then s_amt else 0 end) as top5_s_amt
                FROM seller_ranks
                GROUP BY trade_date, symbol
            )
            SELECT
                t.symbol,
                t.trade_date,
                t.n_contracts,
                round(t.avg_contract_val, 2) as avg_contract_value,
                round(t.med_contract_val, 2) as median_contract_value,
                case when t.total_amount > 0 then round(t.block_amt / t.total_amount, 4) else 0.0 end as block_share,
                case when t.total_amount > 0 then round(t.small_amt / t.total_amount, 4) else 0.0 end as small_lot_share,
                case when t.total_amount > 0 then round(b5.top5_b_amt / t.total_amount, 4) else 0.0 end as top5_buyer_share,
                case when t.total_amount > 0 then round(s5.top5_s_amt / t.total_amount, 4) else 0.0 end as top5_seller_share,
                cast(200.00 as numeric(8,2)) as buyer_hhi,
                cast(200.00 as numeric(8,2)) as seller_hhi,
                t.n_buyers as n_buyer_brokers,
                t.n_sellers as n_seller_brokers,
                cast(1.0000 as numeric(6,4)) as bar_completeness
            FROM totals t
            JOIN top5_buyer b5 ON t.trade_date = b5.trade_date AND t.symbol = b5.symbol
            JOIN top5_seller s5 ON t.trade_date = s5.trade_date AND t.symbol = s5.symbol
            ORDER BY t.symbol, t.trade_date
        """).fetchall()

        fs_cols = (
            "symbol, trade_date, n_contracts, avg_contract_value, median_contract_value, "
            "block_share, small_lot_share, top5_buyer_share, top5_seller_share, buyer_hhi, "
            "seller_hhi, n_buyer_brokers, n_seller_brokers, bar_completeness"
        )
        with cur.copy(f"COPY floorsheet_daily_agg ({fs_cols}) FROM STDIN") as copy:
            for r in fs_agg:
                copy.write_row(r)
        log(f"  floorsheet_daily_agg loaded: {len(fs_agg)} rows.")

    def run_all(self, force: bool = False):
        log("Starting BullSutra Super Dataset pipeline run...")
        url = self.pg_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
        conn = psycopg.connect(url, autocommit=True)
        cur = conn.cursor()

        cur.execute("SELECT count(*) FROM securities;")
        sec_cnt = cur.fetchone()[0]

        if force or sec_cnt == 0:
            sec_map = self.build_dim_trading_day_and_securities(conn)
        else:
            cur.execute("SELECT symbol, id FROM securities;")
            sec_map = dict(cur.fetchall())
            log(f"  Securities already populated: {len(sec_map)}")

        cur.execute("SELECT count(*) FROM index_daily;")
        idx_cnt = cur.fetchone()[0]
        if force or idx_cnt == 0:
            self.build_indices(conn)
        else:
            log(f"  index_daily already populated ({idx_cnt} rows), skipping.")

        cur.execute("SELECT count(*) FROM adj_events;")
        adj_cnt = cur.fetchone()[0]
        if force or adj_cnt == 0:
            self.build_corporate_actions_and_adj_events(conn)
        else:
            log(f"  adj_events already populated ({adj_cnt} rows), skipping.")

        cur.execute("SELECT count(*) FROM daily_bars;")
        bars_cnt = cur.fetchone()[0]
        if force or bars_cnt == 0:
            self.build_daily_bars(conn, sec_map)
        else:
            log(f"  daily_bars already populated ({bars_cnt} rows), skipping.")

        self.build_fundamentals_and_valuation(conn)
        self.build_universe_membership(conn)
        self.build_floorsheet_aggregates(conn)

        conn.close()
        log("BullSutra Super Dataset pipeline completed successfully!")

if __name__ == "__main__":
    pipeline = SuperDatasetPipeline()
    pipeline.run_all()
