from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.ops import LlmCache

async def get_cached(db: AsyncSession, key: str, model: str) -> Optional[Dict[str, Any]]:
    stmt = select(LlmCache.response).where(
        LlmCache.key == key,
        LlmCache.model == model
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def set_cache(db: AsyncSession, key: str, model: str, response: Dict[str, Any]) -> None:
    stmt = insert(LlmCache).values(
        key=key,
        model=model,
        response=response
    ).on_conflict_do_update(
        index_elements=["key"],
        set_={"model": model, "response": response}
    )
    await db.execute(stmt)
