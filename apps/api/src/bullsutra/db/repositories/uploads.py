import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.ops import Upload

async def create_upload(
    db: AsyncSession,
    upload_type: str,
    filename: str,
    staged_path: str,
    created_by: Optional[str] = None
) -> Upload:
    upload = Upload(
        id=uuid.uuid4(),
        upload_type=upload_type,
        filename=filename,
        staged_path=staged_path,
        status="validated",
        created_by=created_by,
    )
    db.add(upload)
    await db.flush()
    return upload

async def get_upload(db: AsyncSession, upload_id: uuid.UUID) -> Optional[Upload]:
    stmt = select(Upload).where(Upload.id == upload_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def list_uploads(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Upload], int]:
    count_stmt = select(func.count(Upload.id))
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = select(Upload).order_by(Upload.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all()), total

async def update_validation_result(
    db: AsyncSession,
    upload_id: uuid.UUID,
    status: str,
    row_count: int,
    error_count: int,
    errors: List[Any]
) -> None:
    stmt = update(Upload).where(Upload.id == upload_id).values(
        status=status,
        row_count=row_count,
        error_count=error_count,
        errors=errors
    )
    await db.execute(stmt)

async def mark_committed(db: AsyncSession, upload_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    stmt = update(Upload).where(Upload.id == upload_id).values(
        status="committed",
        committed_at=now
    )
    await db.execute(stmt)
