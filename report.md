# Assignment 4 — Part 4.2 Report (complete submission details before uploading)

## Completed work
Expanded the Part 4.1 AAPL market workstation with configurable short/long simple moving averages, crossover signals, long-only simulated execution, order/fill history, cash and position tracking, realized/unrealized profit and loss, and historical equity/drawdown/return results. The Vue dashboard displays SMA overlays and backtest results. FastAPI exposes `GET /api/backtest?short=10&long=30`.

## Design and assumptions
The strategy uses **only completed one-minute candles**. SMAs are computed on candle closes. A cross above generates a buy signal, and a cross below generates a sell signal. A signal at candle close is executed at the **next completed candle's open** to avoid same-bar lookahead. One long position maximum, integer shares, initial cash $10,000, fixed $1 fee per fill, no margin, short selling, interest, or slippage. A signal at the end of the available history is not filled. Open positions are marked to the last completed close. Unrealized P/L includes entry fee in cost basis; realized P/L includes entry and exit fees. Cash and positions represent the **simulated backtest**, not real brokerage orders.

## Verification
`python -m unittest backend.test_strategy -v` passed three tests: a hand-calculated SMA reference ([1,2,3,4,5,6], 3-period SMA => [undefined,undefined,2,3,4,5]); batch vs prefix/incremental SMA agreement; and a known trading/accounting example. In the example with $100 initial cash and $1 per-fill fee, buy 6 shares at $14 and sell 6 at $7 gives final cash $49 and realized P/L -$51. The test also confirms an unfinished final candle does not execute a trade. GitHub Actions is configured to rerun unit tests and frontend build on push/pull request.

**Still to verify manually:** Launch backend/frontend, confirm chart overlays and browser behavior, inspect backtest results on actual stored AAPL data, verify GitHub Actions run, and record the video. A browser automation suite has **not** been implemented.

## Limitations
Yahoo Finance intraday history may be delayed, incomplete, or revised. Backtests on a short single-symbol sample do not establish profitability or predictive ability. Next-bar open is a simplified execution assumption; no bid/ask spread, slippage, market impact, partial fills, or taxes. No benchmark, out-of-sample evaluation, or corporate-action validation. The backtest is recalculated from stored completed candles; it is not a live broker account. Crossover calculations use finalized stored values and therefore a retrospective revision could change historical signals.

## Supporting documents
- `README.md` — setup and system overview
- `docs/design-notes.md` — architecture notes
- `backend/strategy.py` — signal and accounting logic
- `backend/test_strategy.py` — reproducible verification tests
- `.github/workflows/checks.yml` — push-time automated checks

## GitHub repository
[ADD YOUR PUBLIC OR INSTRUCTOR-ACCESSIBLE REPOSITORY URL]

## Submitted commit
[ADD OUTPUT OF `git rev-parse HEAD` AFTER PUSH]

## Demonstration video (30–60 seconds)
[ADD ACCESSIBLE VIDEO LINK SHOWING SMA LINES, PARAMETERS, SIMULATED ACCOUNT, AND TRADES]
