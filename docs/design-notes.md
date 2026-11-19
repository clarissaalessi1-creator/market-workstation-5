# Design notes
Data flow: Yahoo Finance -> yfinance history poll -> FastAPI -> SQLite -> backend WebSocket -> Vue Lightweight Charts.
The current WebSocket is backend-to-browser only; a direct streaming source connection is still required.
Database is created on FastAPI startup. See README for schema and limitations.
