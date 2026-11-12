import json
from pathlib import Path
import pytest
import pytest_asyncio
import httpx
from bullsutra.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.asyncio
async def test_health_live():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health/live")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_health_ready():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["db"] is True

@pytest.mark.asyncio
async def test_health_freshness():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health/data-freshness")
        assert res.status_code == 200
        data = res.json()
        assert "prices_latest" in data

@pytest.mark.asyncio
async def test_auth_login_and_me():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Invalid credentials -> 401
        res = await client.post("/api/v1/auth/login", json={"email": "sawan@bullsutra.com", "password": "wrongpassword"})
        assert res.status_code == 401
        assert "error" in res.json()

        # Valid credentials -> 200
        res = await client.post("/api/v1/auth/login", json={"email": "sawan@bullsutra.com", "password": "supersecurepassword123"})
        assert res.status_code == 200
        tok_data = res.json()
        assert "access_token" in tok_data
        assert "refresh_token" in tok_data
        access_tok = tok_data["access_token"]
        refresh_tok = tok_data["refresh_token"]

        # Call /auth/me with Bearer token
        res_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_tok}"})
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == "sawan@bullsutra.com"
        assert me_data["role"] == "admin"

        # Refresh token exchange
        res_ref = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
        assert res_ref.status_code == 200
        assert "access_token" in res_ref.json()

        # Admin stats endpoint
        res_stats = await client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {access_tok}"})
        assert res_stats.status_code == 200
        stats_data = res_stats.json()
        assert "counts" in stats_data
        assert "prices" in stats_data["counts"]
        assert isinstance(stats_data["counts"]["prices"], int)

@pytest.mark.asyncio
async def test_api_keys_flow():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login first to get JWT
        res = await client.post("/api/v1/auth/login", json={"email": "sawan@bullsutra.com", "password": "supersecurepassword123"})
        access_tok = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_tok}"}

        # Create API Key
        res_create = await client.post("/api/v1/auth/api-keys", json={"name": "Test Key"}, headers=headers)
        assert res_create.status_code == 201
        key_data = res_create.json()
        raw_key = key_data["key"]
        key_id = key_data["id"]

        # Use API key to call /auth/me
        res_me = await client.get("/api/v1/auth/me", headers={"X-API-Key": raw_key})
        assert res_me.status_code == 200
        assert res_me.json()["kind"] == "api_key"

        # List API keys
        res_list = await client.get("/api/v1/auth/api-keys", headers=headers)
        assert res_list.status_code == 200
        assert any(k["id"] == key_id for k in res_list.json()["items"])

        # Revoke API key
        res_del = await client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=headers)
        assert res_del.status_code == 204

        # Using revoked key returns 401
        res_revoked = await client.get("/api/v1/auth/me", headers={"X-API-Key": raw_key})
        assert res_revoked.status_code == 401

@pytest.mark.asyncio
async def test_securities_endpoints():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # List securities
        res = await client.get("/api/v1/securities?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) > 0
        sym = data["items"][0]["symbol"]

        # Get security detail
        res_detail = await client.get(f"/api/v1/securities/{sym}")
        assert res_detail.status_code == 200
        assert res_detail.json()["symbol"] == sym

        # Get OHLCV
        res_ohlcv = await client.get(f"/api/v1/securities/{sym}/ohlcv")
        assert res_ohlcv.status_code == 200
        assert "candles" in res_ohlcv.json()

        # Get indicators
        res_ind = await client.get(f"/api/v1/securities/{sym}/indicators?names=sma20,rsi14")
        assert res_ind.status_code == 200
        assert "series" in res_ind.json()

        # Invalid indicator returns 422
        res_invalid_ind = await client.get(f"/api/v1/securities/{sym}/indicators?names=invalid_indicator")
        assert res_invalid_ind.status_code == 422

@pytest.mark.asyncio
async def test_openapi_snapshot():
    schema = app.openapi()
    openapi_path = Path(__file__).resolve().parents[3] / "openapi.json"
    assert openapi_path.exists(), "openapi.json must exist"
    with open(openapi_path, "r", encoding="utf-8") as f:
        committed = json.load(f)
    assert schema["info"]["title"] == committed["info"]["title"]
    assert set(schema["paths"].keys()) == set(committed["paths"].keys())
