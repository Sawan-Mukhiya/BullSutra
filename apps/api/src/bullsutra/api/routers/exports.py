import uuid
import json
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.db.session import get_db
from bullsutra.services import export_service

router = APIRouter(prefix="/exports", tags=["exports"])

@router.get("/brief/{brief_id}.json")
async def export_brief_json(
    brief_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    brief_dict, filename = await export_service.export_brief_json(db, brief_id)
    content = json.dumps(brief_dict, indent=2, default=str)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type="application/json", headers=headers)

@router.get("/brief/{brief_id}.csv")
async def export_brief_csv(
    brief_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    csv_str, filename = await export_service.export_brief_csv(db, brief_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_str, media_type="text/csv", headers=headers)

@router.get("/brief/{brief_id}.pdf")
async def export_brief_pdf(
    brief_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    pdf_bytes, filename = await export_service.export_brief_pdf(db, brief_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/backtest/{backtest_id}/trades.csv")
async def export_backtest_trades_csv(
    backtest_id: uuid.UUID,
    strategy: str = "full",
    db: AsyncSession = Depends(get_db)
):
    csv_str, filename = await export_service.export_backtest_trades_csv(db, backtest_id, strategy=strategy)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_str, media_type="text/csv", headers=headers)

@router.get("/backtest/{backtest_id}/equity.csv")
async def export_backtest_equity_csv(
    backtest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    csv_str, filename = await export_service.export_backtest_equity_csv(db, backtest_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_str, media_type="text/csv", headers=headers)
