import unittest
from datetime import datetime, timedelta, timezone
from .strategy import moving_average, run_backtest

class StrategyTests(unittest.TestCase):
    def test_sma_reference_and_incremental(self):
        values = [1,2,3,4,5,6]
        self.assertEqual(moving_average(values,3), [None,None,2,3,4,5])
        for n in range(1,len(values)+1):
            self.assertEqual(moving_average(values[:n],3), moving_average(values,3)[:n])

    def test_no_lookahead_and_accounting(self):
        values = [10,10,10,12,14,8,7]
        start = datetime(2026,1,1,tzinfo=timezone.utc)
        rows = [{'candle_time': (start+timedelta(minutes=i)).isoformat(), 'open':p, 'close':p,
                 'is_complete':1} for i,p in enumerate(values)]
        result = run_backtest(rows,2,3,100,1)
        self.assertEqual([(t['side'],t['price']) for t in result['trades']], [('BUY',14),('SELL',7)])
        self.assertEqual(result['account']['shares'],0)
        self.assertEqual(result['account']['cash'],49)
        self.assertEqual(result['account']['realized_pnl'],-51)
        # Incomplete last bar must not affect signals or fills
        rows[-1]['is_complete']=0
        self.assertEqual(len(run_backtest(rows,2,3)['trades']),1)

    def test_parameters(self):
        with self.assertRaises(ValueError):
            run_backtest([],10,10)

if __name__ == '__main__':
    unittest.main()
