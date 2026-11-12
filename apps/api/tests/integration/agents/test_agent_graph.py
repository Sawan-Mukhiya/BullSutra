"""Integration test for full LangGraph research workflow."""
from datetime import date
import pytest
from bullsutra.db.session import async_session_factory
from bullsutra.db.repositories.securities import search
from bullsutra.db.repositories.calendar import get_latest_trading_day
from bullsutra.agents.graph.runner import run_research
from bullsutra.db.repositories.briefs import get_brief_by_id
import uuid

class MockJobContext:
    def __init__(self, session_factory):
        self.job_id = uuid.uuid4()
        self.session_factory = session_factory
        self.events = []
        self.progress = 0.0

    def session(self):
        return self.session_factory()

    async def emit(self, event_type: str, data=None, **kwargs):
        self.events.append((event_type, data))

    async def set_progress(self, val: float, phase=None):
        self.progress = val

@pytest.mark.asyncio
async def test_agent_graph_execution_and_persistence():
    """Run research graph on seeded DB security with use_llm=False."""
    async with async_session_factory() as db:
        secs, _ = await search(db, limit=1)
        if not secs:
            pytest.skip("No securities found in test database")
        sec = secs[0]

        latest_day = await get_latest_trading_day(db)
        as_of = (latest_day.date if hasattr(latest_day, "date") else latest_day.trade_date) if latest_day else date.today()

    ctx = MockJobContext(async_session_factory)
    brief_id_str = await run_research(ctx, sec.id, as_of, use_llm=False)

    assert brief_id_str is not None
    b_uuid = uuid.UUID(brief_id_str)

    async with async_session_factory() as db:
        brief_row = await get_brief_by_id(db, b_uuid)
        assert brief_row is not None
        assert brief_row.security_id == sec.id
        assert brief_row.label in ("BUY", "HOLD", "SELL")
        assert brief_row.brief is not None
        assert brief_row.brief["symbol"] == sec.symbol
        assert len(brief_row.brief["agents"]) == 4

    # Assert events were emitted in expected order
    event_names = [e[0] for e in ctx.events]
    assert "node_started" in event_names
    assert "node_finished" in event_names
