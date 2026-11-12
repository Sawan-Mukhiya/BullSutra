import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.backtests import (
    BacktestRun,
    BacktestStrategyResult,
    BacktestEquity,
    BacktestTrade,
    BacktestFold,
)

async def create_run(db: AsyncSession, data: Dict[str, Any]) -> BacktestRun:
    run_id = data.get("id") or uuid.uuid4()
    data["id"] = run_id
    run = BacktestRun(**data)
    db.add(run)
    await db.flush()
    return run

async def update_status(
    db: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    summary: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> None:
    values: Dict[str, Any] = {"status": status}
    if status == "running":
        values["started_at"] = datetime.now()
    elif status in ("succeeded", "failed"):
        values["finished_at"] = datetime.now()
    if summary is not None:
        values["summary"] = summary
    if error is not None:
        values["error"] = error

    stmt = update(BacktestRun).where(BacktestRun.id == run_id).values(**values)
    await db.execute(stmt)

async def insert_strategy_results(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(BacktestStrategyResult).values(rows)
    res = await db.execute(stmt)
    return res.rowcount

async def insert_equity(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(BacktestEquity).values(rows)
    res = await db.execute(stmt)
    return res.rowcount

async def insert_trades(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(BacktestTrade).values(rows)
    res = await db.execute(stmt)
    return res.rowcount

async def insert_folds(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(BacktestFold).values(rows)
    res = await db.execute(stmt)
    return res.rowcount

async def get_run(db: AsyncSession, run_id: uuid.UUID) -> Optional[BacktestRun]:
    stmt = select(BacktestRun).where(BacktestRun.id == run_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def list_runs(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[BacktestRun], int]:
    count_stmt = select(func.count(BacktestRun.id))
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all()), total

async def get_equity(
    db: AsyncSession,
    run_id: uuid.UUID,
    strategy_key: str
) -> List[BacktestEquity]:
    stmt = select(BacktestEquity).where(
        BacktestEquity.run_id == run_id,
        BacktestEquity.strategy_key == strategy_key
    ).order_by(BacktestEquity.trade_date.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def get_trades(
    db: AsyncSession,
    run_id: uuid.UUID,
    strategy_key: str
) -> List[BacktestTrade]:
    stmt = select(BacktestTrade).where(
        BacktestTrade.run_id == run_id,
        BacktestTrade.strategy_key == strategy_key
    ).order_by(BacktestTrade.entry_date.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def get_strategy_results(db: AsyncSession, run_id: uuid.UUID) -> List[BacktestStrategyResult]:
    stmt = select(BacktestStrategyResult).where(
        BacktestStrategyResult.run_id == run_id
    ).order_by(BacktestStrategyResult.is_benchmark.asc(), BacktestStrategyResult.strategy_key.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def get_folds(db: AsyncSession, run_id: uuid.UUID) -> List[BacktestFold]:
    stmt = select(BacktestFold).where(
        BacktestFold.run_id == run_id
    ).order_by(BacktestFold.fold_idx.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def get_trades_paginated(
    db: AsyncSession,
    run_id: uuid.UUID,
    strategy_key: str,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[BacktestTrade], int]:
    count_stmt = select(func.count(BacktestTrade.id)).where(
        BacktestTrade.run_id == run_id,
        BacktestTrade.strategy_key == strategy_key
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(BacktestTrade).where(
        BacktestTrade.run_id == run_id,
        BacktestTrade.strategy_key == strategy_key
    ).order_by(BacktestTrade.entry_date.asc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all()), total

async def get_equity_all_strategies(
    db: AsyncSession,
    run_id: uuid.UUID,
    strategy_keys: Optional[List[str]] = None
) -> List[BacktestEquity]:
    stmt = select(BacktestEquity).where(BacktestEquity.run_id == run_id)
    if strategy_keys:
        stmt = stmt.where(BacktestEquity.strategy_key.in_(strategy_keys))
    stmt = stmt.order_by(BacktestEquity.strategy_key.asc(), BacktestEquity.trade_date.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())
