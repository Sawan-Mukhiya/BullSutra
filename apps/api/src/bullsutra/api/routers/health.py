from typing import Dict, Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from bullsutra.core.config import settings
from bullsutra.db.session import get_db
from bullsutra.pipelines.freshness import data_freshness

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def health_live() -> Dict[str, str]:
    return {"status": "ok"}

@router.get("/ready")
async def health_ready(response: Response, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    db_ok = False
    try:
        res = await db.execute(text("SELECT 1"))
        db_ok = (res.scalar() == 1)
    except Exception:
        db_ok = False

    chroma_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            chroma_res = await client.get(f"{settings.CHROMA_URL}/api/v1/heartbeat")
            chroma_ok = (chroma_res.status_code == 200)
    except Exception:
        chroma_ok = False

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "db": False, "chroma": chroma_ok}

    return {"status": "ok", "db": True, "chroma": chroma_ok}

@router.get("/data-freshness")
async def health_data_freshness(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await data_freshness(db)
