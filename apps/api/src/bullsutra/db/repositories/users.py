import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.users import User

async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email.strip().lower())
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def create_user(
    db: AsyncSession,
    email: str,
    password_hash: str,
    role: str = "admin"
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email.strip().lower(),
        password_hash=password_hash,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user

async def update_last_login(db: AsyncSession, user_id: uuid.UUID) -> None:
    stmt = update(User).where(User.id == user_id).values(last_login_at=datetime.now(timezone.utc))
    await db.execute(stmt)

async def update_password(db: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
    stmt = update(User).where(User.id == user_id).values(password_hash=password_hash)
    await db.execute(stmt)

async def list_users(db: AsyncSession) -> List[User]:
    stmt = select(User).order_by(User.created_at.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())
