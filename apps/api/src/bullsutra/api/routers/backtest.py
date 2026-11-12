import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.core.errors import NotFound
from bullsutra.core.security import Principal
from bullsutra.api.deps import require_admin
from bullsutra.db.session import get_db
from bullsutra.db.repositories import backtests
from bullsutra.schemas.common import Page
from bullsutra.schemas.backtest import (
    CreateBacktestRequest,
    CreateBacktestResponse,
    BacktestListItem,
    BacktestDetail,
    StrategyResult,
    TradeOut,
    FoldOut,
    EquityResponse,
    EquityPoint,
    FoldsResponse,
)
from bullsutra.backtest.constants import STRATEGY_LABELS
from bullsutra.services import backtest_service

router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.post("", response_model=CreateBacktestResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_backtest(
    req: CreateBacktestRequest,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    backtest_id, job_id = await backtest_service.create(db, p, name=req.name, config=req.config)
    return CreateBacktestResponse(
        status="queued",
        job_id=job_id,
        backtest_id=backtest_id,
        events_url=f"/api/v1/agents/runs/{job_id}/events"
    )

@router.get("", response_model=Page[BacktestListItem])
async def list_backtests(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    runs, total = await backtests.list_runs(db, limit=limit, offset=offset)
    items = [
        BacktestListItem(
            id=str(r.id),
            name=r.name,
            status=r.status,
            created_at=r.created_at,
            finished_at=r.finished_at,
            summary=r.summary,
        )
        for r in runs
    ]
    return Page(items=items, total=total, limit=limit, offset=offset)

@router.get("/{backtest_id}", response_model=BacktestDetail)
async def get_backtest(
    backtest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    run = await backtests.get_run(db, backtest_id)
    if not run:
        raise NotFound(f"Backtest '{backtest_id}' not found")

    raw_strategies = await backtests.get_strategy_results(db, backtest_id)
    strategies = [
        StrategyResult(
            strategy_key=s.strategy_key,
            label=STRATEGY_LABELS.get(s.strategy_key, s.strategy_key),
            is_benchmark=s.is_benchmark,
            metrics=s.metrics or {},
            bootstrap=s.bootstrap,
        )
        for s in raw_strategies
    ]

    return BacktestDetail(
        id=str(run.id),
        name=run.name,
        status=run.status,
        config=run.config or {},
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        strategies=strategies,
    )

@router.get("/{backtest_id}/equity", response_model=EquityResponse)
async def get_backtest_equity(
    backtest_id: uuid.UUID,
    strategies: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    run = await backtests.get_run(db, backtest_id)
    if not run:
        raise NotFound(f"Backtest '{backtest_id}' not found")

    filter_keys = [k.strip() for k in strategies.split(",") if k.strip()] if strategies else None
    equity_rows = await backtests.get_equity_all_strategies(db, backtest_id, strategy_keys=filter_keys)

    series_map: Dict[str, List[EquityPoint]] = {}
    for eq in equity_rows:
        k = eq.strategy_key
        if k not in series_map:
            series_map[k] = []
        series_map[k].append(EquityPoint(
            date=eq.trade_date,
            equity=float(eq.equity),
            drawdown=float(eq.drawdown),
            exposure=float(eq.exposure),
        ))

    return EquityResponse(series=series_map)

@router.get("/{backtest_id}/trades", response_model=Page[TradeOut])
async def get_backtest_trades(
    backtest_id: uuid.UUID,
    strategy: str = "full",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    run = await backtests.get_run(db, backtest_id)
    if not run:
        raise NotFound(f"Backtest '{backtest_id}' not found")

    trades, total = await backtests.get_trades_paginated(db, backtest_id, strategy_key=strategy, limit=limit, offset=offset)
    items = [
        TradeOut(
            symbol=t.symbol,
            entry_date=t.entry_date,
            exit_date=t.exit_date,
            entry_price=float(t.entry_price),
            exit_price=float(t.exit_price) if t.exit_price is not None else None,
            shares=t.shares,
            gross_pnl=float(t.gross_pnl) if t.gross_pnl is not None else 0.0,
            costs=float(t.costs) if t.costs is not None else 0.0,
            tax=float(t.tax) if t.tax is not None else 0.0,
            net_pnl=float(t.net_pnl) if t.net_pnl is not None else 0.0,
            return_pct=float(t.return_pct) if t.return_pct is not None else 0.0,
            holding_days=t.holding_days,
            exit_reason=t.exit_reason,
        )
        for t in trades
    ]
    return Page(items=items, total=total, limit=limit, offset=offset)

@router.get("/{backtest_id}/folds", response_model=FoldsResponse)
async def get_backtest_folds(
    backtest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    run = await backtests.get_run(db, backtest_id)
    if not run:
        raise NotFound(f"Backtest '{backtest_id}' not found")

    raw_folds = await backtests.get_folds(db, backtest_id)
    items = [
        FoldOut(
            fold_idx=f.fold_idx,
            train_start=f.train_start,
            train_end=f.train_end,
            test_start=f.test_start,
            test_end=f.test_end,
            weights=f.weights or {},
            metrics=f.metrics or {},
        )
        for f in raw_folds
    ]
    return FoldsResponse(items=items)
