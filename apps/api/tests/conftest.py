import pytest
from bullsutra.db.session import engine

@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await engine.dispose()
