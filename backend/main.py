import asyncio
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .strategy import run_backtest

DB = Path(__file__).with_name('market.sqlite3')
SYMBOL = 'AAPL'
INTERVAL = '1m'
POLL_SECONDS = 20


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    connection = sqlite3.connect(DB, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS observations (
            symbol TEXT NOT NULL,
            candle_time TEXT NOT NULL,
            open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
            close REAL NOT NULL, volume INTEGER NOT NULL,
            source TEXT NOT NULL, source_time TEXT NOT NULL,
            received_at TEXT NOT NULL, is_complete INTEGER NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY(symbol, candle_time)
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS observation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, candle_time TEXT NOT NULL,
            received_at TEXT NOT NULL, event_type TEXT NOT NULL,
            revision INTEGER NOT NULL, payload TEXT NOT NULL
        )''')


def fetch_candles():
    # Yahoo Finance intraday data may be delayed or unavailable.
    frame = yf.Ticker(SYMBOL).history(period='1d', interval=INTERVAL, auto_adjust=False)
    if frame.empty:
        return []
    receipt = utc_now()
    now = datetime.now(timezone.utc)
    output = []
    for ts, row in frame.iterrows():
        candle_start = ts.to_pydatetime()
        # 1-minute bars are complete only after their minute has ended.
        complete = (now - candle_start.astimezone(timezone.utc)).total_seconds() >= 60
        output.append({
            'symbol': SYMBOL, 'time': candle_start.isoformat(),
            'open': float(row['Open']), 'high': float(row['High']),
            'low': float(row['Low']), 'close': float(row['Close']),
            'volume': int(row['Volume']), 'source': 'Yahoo Finance',
            'source_time': candle_start.isoformat(), 'received_at': receipt,
            'is_complete': complete,
        })
    return output


def save_candles(candles):
    counts = {'inserted': 0, 'revised': 0, 'duplicates': 0}
    with connect() as db:
        for candle in sorted(candles, key=lambda c: c['time']):
            key = (candle['symbol'], candle['time'])
            previous = db.execute('SELECT * FROM observations WHERE symbol=? AND candle_time=?', key).fetchone()
            values = (candle['open'], candle['high'], candle['low'], candle['close'], candle['volume'], int(candle['is_complete']))
            old_values = None if previous is None else tuple(previous[k] for k in ('open', 'high', 'low', 'close', 'volume', 'is_complete'))
            if old_values == values:
                counts['duplicates'] += 1
                continue
            revision = 1 if previous is None else previous['revision'] + 1
            event_type = 'inserted' if previous is None else 'revised'
            db.execute('''INSERT INTO observations
                (symbol,candle_time,open,high,low,close,volume,source,source_time,received_at,is_complete,revision)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol,candle_time) DO UPDATE SET
                open=excluded.open,high=excluded.high,low=excluded.low,
                close=excluded.close,volume=excluded.volume,source=excluded.source,
                source_time=excluded.source_time,received_at=excluded.received_at,
                is_complete=excluded.is_complete,revision=excluded.revision''',
                (*key, *values[:5], candle['source'], candle['source_time'], candle['received_at'], values[5], revision))
            db.execute('''INSERT INTO observation_events
                (symbol,candle_time,received_at,event_type,revision,payload)
                VALUES (?,?,?,?,?,?)''',
                (*key, candle['received_at'], event_type, revision, json.dumps(candle)))
            counts[event_type] += 1
    return counts


def stored_candles():
    with connect() as db:
        rows = db.execute('SELECT * FROM observations WHERE symbol=? ORDER BY candle_time', (SYMBOL,)).fetchall()
        return [dict(row) for row in rows]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title='Market Workstation', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET'], allow_headers=['*'])


@app.get('/api/health')
def health():
    return {'ok': True, 'symbol': SYMBOL, 'source': 'Yahoo Finance'}


@app.get('/api/candles')
def candles():
    return {'symbol': SYMBOL, 'candles': stored_candles()}


@app.get('/api/backtest')
def backtest(short: int = 10, long: int = 30):
    from fastapi import HTTPException
    try:
        return run_backtest(stored_candles(), short=short, long=long)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get('/api/events')
def events():
    with connect() as db:
        rows = db.execute('SELECT * FROM observation_events ORDER BY id DESC LIMIT 100').fetchall()
        return [dict(row) for row in rows]


@app.websocket('/ws/market')
async def market(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                incoming = await asyncio.to_thread(fetch_candles)
                if incoming:
                    changes = await asyncio.to_thread(save_candles, incoming)
                    await websocket.send_json({
                        'status': 'receiving', 'source': 'Yahoo Finance',
                        'received_at': utc_now(), 'changes': changes,
                        'candles': await asyncio.to_thread(stored_candles),
                    })
                else:
                    await websocket.send_json({
                        'status': 'unavailable', 'received_at': utc_now(),
                        'message': 'Yahoo Finance returned no intraday observations',
                        'candles': await asyncio.to_thread(stored_candles),
                    })
            except Exception as exc:
                await websocket.send_json({
                    'status': 'error', 'received_at': utc_now(),
                    'message': str(exc),
                    'candles': await asyncio.to_thread(stored_candles),
                })
            await asyncio.sleep(POLL_SECONDS)
    except (WebSocketDisconnect, RuntimeError):
        pass
