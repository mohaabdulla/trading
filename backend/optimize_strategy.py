import backtester
import strategy
import sys
import contextlib
import itertools
import time

max_holds = [10, 12, 15]
targets = [4.0, 5.0]
stops = [1.8, 2.0]
risks = [0.04, 0.05]

combinations = list(itertools.product(max_holds, targets, stops, risks))
print(f"Testing {len(combinations)} combinations...")

results = []
start_time = time.time()

for idx, (h, t, s, r) in enumerate(combinations):
    strategy.MAX_HOLD_DAYS = h
    strategy.ATR_TARGET_MULTIPLIER = t
    strategy.ATR_STOP_MULTIPLIER = s
    strategy.RISK_PCT = r
    
    # Also need to make sure backtester uses the updated strategy values
    backtester.MAX_HOLD_DAYS = h
    backtester.ATR_TARGET_MULTIPLIER = t
    backtester.ATR_STOP_MULTIPLIER = s
    backtester.RISK_PCT = r
    
    res = backtester.run_backtest(initial_capital=1000.0, start_date="2020-01-01", use_time_stop=True, zero_commission=False)
    metrics = res['metrics']
    
    results.append({
        'hold': h,
        'target': t,
        'stop': s,
        'risk': r,
        'return_pct': metrics['total_return_pct'],
        'net_profit': metrics['net_profit'],
        'win_rate': metrics['win_rate'],
        'trades': metrics['closed_trades'],
        'drawdown': metrics['max_drawdown_pct']
    })
    
    print(f"[{idx+1}/{len(combinations)}] H={h}, T={t}, S={s}, R={r} -> Return: {metrics['total_return_pct']}% | Net: ${metrics['net_profit']} | DD: {metrics['max_drawdown_pct']}%")

print(f"\nDone in {time.time() - start_time:.1f} seconds.\n")
print("--- TOP 5 RESULTS BY RETURN ---")
results.sort(key=lambda x: x['return_pct'], reverse=True)
for r in results[:5]:
    print(f"Return: {r['return_pct']}% | Net: ${r['net_profit']} | Hold: {r['hold']} | Target: {r['target']}x | Stop: {r['stop']}x | Risk: {r['risk']} | WinRate: {r['win_rate']}% | Trades: {r['trades']} | DD: {r['drawdown']}%")
