# BullSutra

> **Multi-Agent Equity Research & Quantitative Consensus Engine for the Nepal Stock Exchange (NEPSE)**

BullSutra is an open-source, full-stack quantitative research platform engineered specifically for the Nepal Stock Exchange (NEPSE). It fuses deterministic technical signals, sector-aware fundamental scoring, financial sentiment analysis, and downside risk gating into an iterative multi-agent debate system orchestrated with **LangGraph**, **FastAPI**, and **Next.js**.

---

## Key Highlights

- **Multi-Specialist Agent Consensus**:
  - **Technicals Specialist**: Vectorized momentum, trend alignment, and breakout detection (SMA 50/200, MACD, RSI 14, Donchian 55 breakout, ATR, and volume surge).
  - **Fundamentals Specialist**: Sector-group scoring tailored for NEPSE regimes (Commercial Banks, Hydropower, Insurance, and Others), evaluating ROE, PE, PBV, and YoY quarterly EPS growth with recency decay.
  - **News & Sentiment Specialist**: Point-in-time financial news sentiment extraction via FinBERT (`ProsusAI/finbert`) with exponential time-decay weighting.
  - **Risk & Liquidity Specialist**: Downside risk gating, 60-day annualized volatility, 120-day maximum drawdown, turnover/zero-volume illiquidity penalties, and NEPSE circuit-breaker regime checks.
- **Debate & Calibration Graph**:
  - LangGraph StateGraph orchestration executing parallel specialist analysis, multi-agent cross-checks, and consensus stabilization.
  - Isotonic probability calibration and historical hit-rate weighting.
  - LLM-powered narrative briefing (Gemini / Ollama / OpenAI-compatible) protected by deterministic numeric guards against hallucinations.
- **Modern Interactive Web Interface**:
  - Built with Next.js (App Router), React 19, Tailwind CSS, and Radix UI.
  - Financial charting powered by Lightweight Charts.
  - Real-time Server-Sent Events (SSE) streaming of agent thought processes and research briefs.

---

## Repository Structure

```
BullSutra_v0/
├── apps/
│   ├── .env.example           # Backend environment configuration template
│   ├── api/                   # Python FastAPI Backend
│   │   ├── alembic/           # PostgreSQL migration versions
│   │   ├── config/            # System YAML configuration (news sources, etc.)
│   │   ├── src/bullsutra/
│   │   │   ├── agents/        # Specialists, consensus debate, LangGraph nodes & LLM narrators
│   │   │   ├── core/          # App settings, DB engine, security & rate limiting
│   │   │   ├── models/        # SQLAlchemy relational schema models
│   │   │   ├── pipelines/     # DuckDB data processing & historical ingestion
│   │   │   ├── repositories/  # Database data access layer
│   │   │   ├── routers/       # REST API endpoints (agents, auth, stocks, backtest)
│   │   │   └── main.py        # FastAPI application entrypoint
│   │   ├── tests/             # Backend test suite (pytest + pytest-asyncio)
│   │   └── pyproject.toml     # Python dependencies and build config
│   └── .gitignore
├── web/                       # Next.js 16 + React 19 Web Client
│   ├── src/                   # Components, hooks, types, and App router pages
│   ├── public/                # Static assets & SVG icons
│   ├── .env.example           # Frontend environment configuration template
│   ├── package.json           # Node.js dependencies and scripts
│   └── tsconfig.json          # TypeScript configuration
├── .gitignore                 # Root gitignore rules
└── README.md                  # Project documentation
```

---

## Getting Started

### Prerequisites

- **Python**: `>= 3.11` (recommended: install with [uv](https://github.com/astral-sh/uv))
- **Node.js**: `>= 18.x` (or `pnpm` / `npm`)
- **PostgreSQL**: `>= 15.x` with `citext` extension enabled
- *(Optional)* **Ollama**: For local offline LLM inference (`qwen2.5:3b-instruct` or similar)
- *(Optional)* **Google Gemini API Key**: For hosted LLM narrative synthesis

---

### 1. Backend Setup (FastAPI & Agent Engine)

1. **Navigate to the backend directory**:
   ```bash
   cd apps/api
   ```

2. **Set up a Python virtual environment & install dependencies**:
   ```bash
   # Using uv (fastest):
   uv venv
   source .venv/bin/activate   # On Windows PowerShell: .venv\Scripts\Activate.ps1
   uv pip install -e ".[dev]"

   # Or using standard pip:
   python -m venv .venv
   source .venv/bin/activate   # On Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

3. **Configure the Environment**:
   Copy the example environment file from `apps/.env.example`:
   ```bash
   cp ../.env.example .env
   ```
   Open `.env` and fill in:
   - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` (PostgreSQL connection strings).
   - `JWT_SECRET` and `API_KEY_PEPPER` (generate secure random hex strings).
   - `GOOGLE_API_KEY` (if using Google Gemini for narrative reports).

4. **Prepare the Database & Run Migrations**:
   Ensure PostgreSQL is running and initialize the schema:
   ```sql
   CREATE DATABASE bullsutra;
   \c bullsutra
   CREATE EXTENSION IF NOT EXISTS citext;
   ```
   Apply Alembic migrations:
   ```bash
   alembic upgrade head
   ```

5. **Start the API Server**:
   ```bash
   uvicorn bullsutra.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The interactive API documentation will be available at:
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

6. *(Optional)* **Start the Background Worker**:
   ```bash
   python -m bullsutra.worker
   ```

---

### 2. Frontend Setup (Next.js Web Client)

1. **Navigate to the web directory**:
   ```bash
   cd web
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   # or with pnpm
   pnpm install
   ```

3. **Configure Frontend Environment**:
   ```bash
   cp .env.example .env.local
   ```
   Verify that `API_INTERNAL_URL` points to `http://localhost:8000`.

4. **Run the Development Server**:
   ```bash
   npm run dev
   # or with pnpm
   pnpm dev
   ```

5. **Access the Web Dashboard**:
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Configuration Reference

Key variables inside `apps/.env`:

| Variable | Description | Default / Example |
|---|---|---|
| `ENV` | Application environment (`local`, `test`, `prod`) | `local` |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:pass@localhost:5432/bullsutra` |
| `DATABASE_URL_SYNC` | Sync PostgreSQL connection string (for Alembic migrations) | `postgresql+psycopg://postgres:pass@localhost:5432/bullsutra` |
| `JWT_SECRET` | Secret key for JWT session tokens | *Generate via `openssl rand -hex 32`* |
| `API_KEY_PEPPER` | Pepper string for API key hashing | *Generate via `openssl rand -hex 16`* |
| `LLM_PROVIDER` | Primary narrator LLM (`gemini`, `ollama`, `omniroute`, `fake`) | `gemini` |
| `LLM_MODEL` | Primary model identifier | `gemini-2.5-flash` |
| `GOOGLE_API_KEY` | Google Gemini API key | `your_google_gemini_api_key` |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | `http://localhost:11434` |
| `DATASETS_DIR` | Directory containing DuckDB / Parquet dataset files | `./data/datasets` |

---

## Running Tests

### Backend Test Suite
```bash
cd apps/api
pytest
```

### Frontend Test Suite & Type Checking
```bash
cd web
npm run typecheck
npm run test
```

---

## Disclaimer

BullSutra is designed for quantitative market research and educational purposes. Financial signals and multi-agent consensus outputs do not constitute investment advice. Always conduct your own independent due diligence before making financial decisions on the Nepal Stock Exchange (NEPSE).
