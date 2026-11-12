import uuid
from typing import Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError as PydanticValidationError

from bullsutra.core.errors import ValidationError
from bullsutra.core.security import Principal
from bullsutra.backtest.config import BacktestConfig
from bullsutra.db.repositories import backtests, jobs
from bullsutra.worker.context import JobContext

async def create(db: AsyncSession, principal: Principal, name: str, config: Dict[str, Any]) -> Tuple[str, str]:
    try:
        validated_config = BacktestConfig.model_validate(config or {})
    except PydanticValidationError as e:
        raise ValidationError(f"Invalid backtest config: {e.errors()}", details={"errors": e.errors()})

    run = await backtests.create_run(db, {
        "name": name,
        "config": validated_config.model_dump(mode="json"),
        "status": "queued",
        "created_by": principal.id if principal else None,
    })
    
    job = await jobs.enqueue(
        db,
        kind="backtest",
        payload={
            "backtest_id": str(run.id),
            "name": name,
            "config": validated_config.model_dump(mode="json"),
        },
        created_by=principal.id if principal else None
    )
    
    await db.commit()
    return str(run.id), str(job.id)

async def run_backtest_job(ctx: JobContext) -> Dict[str, Any]:
    from bullsutra.backtest.runner import run_backtest
    backtest_id = uuid.UUID(ctx.payload["backtest_id"])
    return await run_backtest(ctx, backtest_id)
