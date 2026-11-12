import uuid
import pytest
import httpx
from datetime import date
from bullsutra.main import app
from bullsutra.db.session import async_session_factory
from bullsutra.db.models.agents import ResearchBriefRow
from bullsutra.db.repositories import securities

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.asyncio
async def test_exports_and_brief():
    # Insert a dummy brief in DB adhering to ResearchBrief contract
    brief_id = uuid.uuid4()
    dummy_brief = {
        "id": str(brief_id),
        "symbol": "NABIL",
        "company_name": "Nabil Bank Limited",
        "sector": "Commercial Banks",
        "as_of": "2026-03-25",
        "signal": {
            "label": "BUY",
            "score": 0.65,
            "raw_confidence": 0.70,
            "confidence": 0.75,
            "position_multiplier": 0.8,
            "conflicted": False,
            "flags": []
        },
        "agents": {
            "news": {
                "agent": "news",
                "score": 0.5,
                "confidence": 0.6,
                "drivers": [{"kind": "news", "note": "Positive earnings sentiment", "ref": "article:123"}],
                "risks": [],
                "flags": [],
                "meta": {}
            },
            "fundamentals": {
                "agent": "fundamentals",
                "score": 0.7,
                "confidence": 0.8,
                "drivers": [{"kind": "fundamental", "note": "ROE above 15%", "ref": "ROE"}],
                "risks": [],
                "flags": [],
                "meta": {}
            },
            "technicals": {
                "agent": "technicals",
                "score": 0.6,
                "confidence": 0.7,
                "drivers": [{"kind": "indicator", "note": "Breakout above SMA50", "ref": "SMA50"}],
                "risks": [],
                "flags": [],
                "meta": {}
            },
            "risk": {
                "agent": "risk",
                "score": 0.2,
                "confidence": 0.9,
                "drivers": [{"kind": "risk", "note": "Low annualized volatility", "ref": "vol60"}],
                "risks": [],
                "flags": [],
                "meta": {}
            }
        },
        "debate": {"triggered": False, "initial_disagreement": 0.1, "final_disagreement": 0.1, "cross_checks": [], "rounds": []},
        "drivers": [{"note": "Strong ROE", "kind": "fundamental", "ref": "ROE", "value": 15.2}],
        "risks": ["General market volatility"],
        "risk_flags": [],
        "sources": [{"type": "news", "label": "Bizmandu Q3 Report"}],
        "summary": "NABIL shows strong technical and fundamental alignment.",
        "meta": {
            "graph_version": "1.0.0",
            "logic_version": "1.0.0",
            "prompt_version": None,
            "llm_model": None,
            "used_llm": False,
            "weights": {"news": 1.0, "fundamentals": 1.0, "technicals": 1.0},
            "price_date": "2026-03-25",
            "news_cutoff": "2026-03-25T16:00:00Z",
            "generated_at": "2026-03-25T16:15:00Z"
        },
        "disclaimer": "BullSutra disclaimer"
    }

    async with async_session_factory() as session:
        sec = await securities.get_by_symbol(session, "NABIL")
        assert sec is not None
        brief_row = ResearchBriefRow(
            id=brief_id,
            security_id=sec.id,
            as_of=date.fromisoformat("2026-03-25"),
            label="BUY",
            consensus_score=0.65,
            raw_confidence=0.70,
            confidence=0.75,
            position_multiplier=0.8,
            conflicted=False,
            brief=dummy_brief,
            used_llm=False
        )
        session.add(brief_row)
        await session.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # GET /research/briefs/{brief_id}
        res_b = await client.get(f"/api/v1/research/briefs/{brief_id}")
        assert res_b.status_code == 200
        assert res_b.json()["symbol"] == "NABIL"

        # GET /research/NABIL
        res_sym = await client.get("/api/v1/research/NABIL")
        assert res_sym.status_code == 200
        assert res_sym.json()["symbol"] == "NABIL"

        # GET /exports/brief/{brief_id}.json
        res_json = await client.get(f"/api/v1/exports/brief/{brief_id}.json")
        assert res_json.status_code == 200
        assert res_json.headers["content-type"].startswith("application/json")
        assert 'filename="bullsutra_NABIL_2026-03-25.json"' in res_json.headers["content-disposition"]

        # GET /exports/brief/{brief_id}.csv
        res_csv = await client.get(f"/api/v1/exports/brief/{brief_id}.csv")
        assert res_csv.status_code == 200
        csv_lines = res_csv.text.strip().split("\n")
        assert len(csv_lines) == 5  # 1 header + 4 rows (news, fundamentals, technicals, risk)
        assert csv_lines[0].startswith("symbol,as_of,label")
        assert "news" in csv_lines[1]
        assert "fundamentals" in csv_lines[2]
        assert "technicals" in csv_lines[3]
        assert "risk" in csv_lines[4]

        # GET /exports/brief/{brief_id}.pdf
        res_pdf = await client.get(f"/api/v1/exports/brief/{brief_id}.pdf")
        assert res_pdf.status_code == 200
        assert res_pdf.content.startswith(b"%PDF")

@pytest.mark.asyncio
async def test_uploads_validate_and_commit():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login
        res_login = await client.post("/api/v1/auth/login", json={"email": "sawan@bullsutra.com", "password": "supersecurepassword123"})
        headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

        # Validate invalid CSV
        csv_invalid = "symbol,trade_date,close,volume\nNABIL,invalid-date,-10,100"
        files = {"file": ("test_invalid.csv", csv_invalid.encode(), "text/csv")}
        res_val_inv = await client.post("/api/v1/uploads/prices_csv/validate", files=files, headers=headers)
        assert res_val_inv.status_code == 200
        assert res_val_inv.json()["status"] == "rejected"
        assert res_val_inv.json()["error_count"] > 0

        # Validate valid CSV
        csv_valid = "symbol,trade_date,open,high,low,close,volume\nNABIL,2026-03-26,450,460,448,455,1000\n"
        files = {"file": ("test_valid.csv", csv_valid.encode(), "text/csv")}
        res_val = await client.post("/api/v1/uploads/prices_csv/validate", files=files, headers=headers)
        assert res_val.status_code == 200
        upload_data = res_val.json()
        assert upload_data["status"] == "validated"
        upload_id = upload_data["id"]

        # Commit upload
        res_commit = await client.post(f"/api/v1/uploads/{upload_id}/commit", headers=headers)
        assert res_commit.status_code == 200
        assert res_commit.json()["status"] == "committed"

        # List uploads
        res_list = await client.get("/api/v1/uploads", headers=headers)
        assert res_list.status_code == 200
        assert any(u["id"] == upload_id for u in res_list.json()["items"])
