# Live Market Workstation — Part 4.1

A local Vue + FastAPI + SQLite dashboard for Yahoo Finance market observations.

## Requirements

Python 3.10+ and Node.js 20+ (with npm).

## Start backend

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Check http://127.0.0.1:8000/api/health and http://127.0.0.1:8000/docs.

## Start frontend

In a **second terminal**, from the project root:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173.

## Architecture

Vue -> browser WebSocket -> FastAPI -> Yahoo Finance history polling (20-second intervals) -> SQLite. FastAPI returns stored candles to the browser over WebSocket and REST. The SQLite database is initialized on backend startup in `backend/market.sqlite3`.

### Schema

- `observations`: one current row per `(symbol, candle_time)`, including source, receipt time, completion flag, and revision.
- `observation_events`: immutable insert/revision events to preserve changes over time.

Repeated identical observations are ignored. Revisions update the existing candle and append an event. Out-of-order candles are sorted before saving. The replay view loads stored observations via `/api/candles`. Source timestamps are provided by Yahoo Finance bar indexes; receipt timestamps are recorded by the backend. Candles are treated as complete once their interval has ended, which is an approximation, not a provider guarantee.

## Current limitations / next work

**This is a runnable foundation, not a finished Part 4.1 submission.** Yahoo Finance is polled through yfinance rather than using Yahoo's real-time streaming socket. The UI refreshes using a backend WebSocket, but this does not prove a live source feed. The assignment requires verifying a live Yahoo Finance streaming connection. The app also needs an automated test suite, a timed replay mode, browser evidence, a proper feed-age heartbeat, and documented feed-unavailable tests. Market data can be delayed, rate limited, or missing outside trading hours. Do not present polling or stored observations as verified live ticks.

No credentials are needed for this starter. Do not commit secrets.

## Part 4.2: indicators and simulated backtesting

Start backend from the project root (with Python dependencies installed):

```bash
python -m uvicorn backend.main:app --reload --port 8001
```

Start frontend in a separate terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the local Vite URL shown in the terminal. The dashboard loads stored AAPL candles and `/api/backtest?short=10&long=30`; short and long SMA windows can be adjusted. No real trades are placed. Tests: `python -m unittest backend.test_strategy -v`. A GitHub Actions workflow runs tests and `npm run build` on pushes.
