"""Deterministic, long-only SMA crossover simulation on completed candles."""
from datetime import datetime


def moving_average(values, window):
    if not isinstance(window, int) or window < 1:
        raise ValueError('window must be a positive integer')
    result = []
    total = 0.0
    for i, value in enumerate(values):
        total += float(value)
        if i >= window:
            total -= float(values[i-window])
        result.append(total/window if i >= window-1 else None)
    return result


def prepare(rows):
    complete = [r for r in rows if bool(r['is_complete'])]
    return sorted(complete, key=lambda r: datetime.fromisoformat(r.get('candle_time', r.get('time'))))


def run_backtest(rows, short=10, long=30, initial_cash=10000.0, fee=1.0):
    if not (isinstance(short, int) and isinstance(long, int) and 1 <= short < long):
        raise ValueError('Require integer SMA windows with 1 <= short < long')
    if initial_cash <= 0 or fee < 0:
        raise ValueError('Invalid cash or fee')
    bars = prepare(rows)
    closes = [float(r['close']) for r in bars]
    fast, slow = moving_average(closes, short), moving_average(closes, long)
    cash, shares, cost_basis, realized = float(initial_cash), 0, 0.0, 0.0
    pending = None
    trades, equity, indicators = [], [], []
    for i, bar in enumerate(bars):
        stamp = bar.get('candle_time', bar.get('time'))
        # Execute yesterday's signal at the NEXT completed bar's open; never use the
        # current bar's close to execute an order at that bar's open.
        if pending:
            price = float(bar['open'])
            if price > 0:
                if pending == 'BUY':
                    quantity = max(0, int((cash-fee)//price))
                    if quantity:
                        amount = quantity*price
                        cash -= amount+fee
                        shares = quantity
                        cost_basis = amount+fee
                        trades.append({'time': stamp, 'side': 'BUY', 'quantity': quantity, 'price': price, 'fee': fee, 'cash_after': round(cash, 2), 'realized_pnl': 0.0})
                elif pending == 'SELL' and shares:
                    proceeds = shares*price-fee
                    pnl = proceeds-cost_basis
                    cash += proceeds
                    realized += pnl
                    trades.append({'time': stamp, 'side': 'SELL', 'quantity': shares, 'price': price, 'fee': fee, 'cash_after': round(cash, 2), 'realized_pnl': round(pnl, 2)})
                    shares, cost_basis = 0, 0.0
            pending = None
        signal = 'HOLD'
        if i > 0 and fast[i] is not None and slow[i] is not None and slow[i-1] is not None:
            if fast[i-1] <= slow[i-1] and fast[i] > slow[i]:
                signal = 'BUY'
                if not shares:
                    pending = 'BUY'
            elif fast[i-1] >= slow[i-1] and fast[i] < slow[i]:
                signal = 'SELL'
                if shares:
                    pending = 'SELL'
        mark = closes[i]
        unrealized = shares*mark-cost_basis if shares else 0.0
        equity.append({'time': stamp, 'equity': round(cash+shares*mark, 2)})
        indicators.append({'time': stamp, 'short_sma': fast[i], 'long_sma': slow[i], 'signal': signal})
    last_price = closes[-1] if closes else 0
    final_equity = cash+shares*last_price
    peak, drawdown = initial_cash, 0.0
    for item in equity:
        peak = max(peak, item['equity'])
        drawdown = max(drawdown, (peak-item['equity'])/peak)
    return {'parameters': {'short': short, 'long': long, 'initial_cash': initial_cash, 'fee_per_fill': fee},
            'assumptions': 'Completed candles only; close-of-bar crossover signal, next bar open execution, integer long-only shares, fixed fee per fill, no slippage or interest; pending final signal not executed; mark-to-market at last close.',
            'bars_used': len(bars), 'indicators': indicators, 'trades': trades, 'equity_curve': equity,
            'account': {'cash': round(cash,2), 'shares': shares, 'last_price': last_price, 'cost_basis': round(cost_basis,2),
                        'realized_pnl': round(realized,2), 'unrealized_pnl': round(shares*last_price-cost_basis,2) if shares else 0.0,
                        'total_equity': round(final_equity,2), 'total_return_pct': round((final_equity/initial_cash-1)*100,2),
                        'max_drawdown_pct': round(drawdown*100,2)}}
