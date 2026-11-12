import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.users import ApiKey

async def get_by_hash(db: AsyncSession, key_hash: str) -> Optional[ApiKey]:
    stmt = select(ApiKey).where(ApiKey.key_hash == key_hash)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def get_by_id(db: AsyncSession, key_id: uuid.UUID) -> Optional[ApiKey]:
    stmt = select(ApiKey).where(ApiKey.id == key_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def list_keys(db: AsyncSession) -> List[ApiKey]:
    stmt = select(ApiKey).order_by(ApiKey.created_at.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def create_key(
    db: AsyncSession,
    name: str,
    key_prefix: str,
    key_hash: str,
    created_by: Optional[uuid.UUID] = None,
    role: str = "admin"
) -> ApiKey:
    api_key = ApiKey(
        id=uuid.uuid4(),
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        role=role,
        is_active=True,
        created_by=created_by,
    )
    db.add(api_key)
    await db.flush()
    return api_key

async def revoke_key(db: AsyncSession, key_id: uuid.UUID) -> bool:
    now = datetime.now(timezone.utc)
    stmt = update(ApiKey).where(ApiKey.id == key_id).values(is_active=False, revoked_at=now)
    res = await db.execute(stmt)
    return res.rowcount > 0

async def update_last_used(db: AsyncSession, key_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    stmt = update(ApiKey).where(ApiKey.id == key_id).values(last_used_at=now)
    await db.execute(stmt)
