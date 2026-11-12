from typing import AsyncIterator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from bullsutra.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)
async_session_factory = async_session

async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
