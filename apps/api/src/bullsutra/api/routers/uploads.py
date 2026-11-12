import uuid
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.core.security import Principal
from bullsutra.api.deps import require_admin
from bullsutra.db.session import get_db
from bullsutra.schemas.common import Page
from bullsutra.schemas.uploads import UploadOut
from bullsutra.services import upload_service

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/{upload_type}/validate", response_model=UploadOut)
async def validate_upload(
    upload_type: str,
    file: UploadFile = File(...),
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    return await upload_service.validate_upload(db, upload_type, file, p)

@router.post("/{upload_id}/commit", response_model=UploadOut)
async def commit_upload(
    upload_id: uuid.UUID,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    return await upload_service.commit_upload(db, upload_id, p)

@router.get("", response_model=Page[UploadOut])
async def list_uploads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    items, total = await upload_service.list_uploads_service(db, limit=limit, offset=offset)
    return Page(items=items, total=total, limit=limit, offset=offset)
