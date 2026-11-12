import uuid
import asyncio
import pytest
import httpx
from datetime import date
from bullsutra.main import app
from bullsutra.db.session import async_session_factory
from bullsutra.db.repositories import jobs
from bullsutra.worker.runner import WorkerRunner
from bullsutra.worker.context import JobContext
from bullsutra.worker.handlers import HANDLERS

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.asyncio
async def test_worker_and_job_execution():
    # Register a test handler that emits events and progress
    async def sample_test_handler(ctx: JobContext):
        await ctx.emit("node_started", node="test_node")
        await ctx.set_progress(0.5, phase="testing")
        await ctx.emit("node_finished", node="test_node", data={"metric": 42})
        return {"status": "ok", "computed": 42}

    HANDLERS["eod_prices"] = sample_test_handler

    # Enqueue job
    async with async_session_factory() as session:
        job = await jobs.enqueue(session, kind="eod_prices", payload={"test": True})
        await session.commit()
        job_id = job.id

    # Run worker on this job
    runner = WorkerRunner(concurrency=1)
    await runner.execute_job(job)

    # Verify job succeeded in DB
    async with async_session_factory() as session:
        finished = await jobs.get_by_id(session, job_id)
        assert finished.status == "succeeded"
        assert finished.progress == 1.0
        assert finished.result == {"status": "ok", "computed": 42}

        # Check emitted events
        events = await jobs.list_events(session, job_id)
        types = [e.event_type for e in events]
        assert "job_started" in types
        assert "node_started" in types
        assert "progress" in types
        assert "node_finished" in types
        assert "job_finished" in types

@pytest.mark.asyncio
async def test_backtest_endpoints():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login
        res_login = await client.post("/api/v1/auth/login", json={"email": "sawan@bullsutra.com", "password": "supersecurepassword123"})
        headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

        # Create Backtest
        res_bt = await client.post(
            "/api/v1/backtest",
            json={"name": "Walk-forward Run 1", "config": {"train_days": 500, "test_days": 100}},
            headers=headers
        )
        assert res_bt.status_code == 202
        bt_data = res_bt.json()
        assert bt_data["status"] == "queued"
        assert "backtest_id" in bt_data
        assert "job_id" in bt_data
        bt_id = bt_data["backtest_id"]

        # List backtests (public)
        res_list = await client.get("/api/v1/backtest")
        assert res_list.status_code == 200
        assert any(b["id"] == bt_id for b in res_list.json()["items"])

        # Get detail (public)
        res_detail = await client.get(f"/api/v1/backtest/{bt_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["name"] == "Walk-forward Run 1"

        # Get equity & trades
        res_eq = await client.get(f"/api/v1/backtest/{bt_id}/equity")
        assert res_eq.status_code == 200
        res_trades = await client.get(f"/api/v1/backtest/{bt_id}/trades")
        assert res_trades.status_code == 200
