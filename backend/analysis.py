import sys
import os
sys.path.insert(0, r'c:\Users\mohamed redha\Desktop\trading\backend')

import backtester
from collections import Counter

res = backtester.run_backtest(1000.0)
trades = res['trades']
buys = [t for t in trades if t['action'] == 'BUY']
sells = [t for t in trades if t['action'] == 'SELL']

print("\n--- TRADES PER SYMBOL ---")
c = Counter([t['symbol'] for t in buys])
for k, v in c.items():
    print(f"{k}: {v}")

print("\n--- PERFORMANCE ---")
total_sells = len(sells)
wins = len([s for s in sells if s.get('pnl', 0) > 0])
win_rate = (wins / total_sells * 100) if total_sells > 0 else 0
net_profit = sum([s.get('pnl', 0) for s in sells])

print(f"Total Completed Trades: {total_sells}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Net Profit: ${net_profit:.2f}")

print("\n--- WORST 10 TRADES ---")
sells.sort(key=lambda x: x.get('pnl', 0))
for s in sells[:10]:
    print(f"{s['symbol']}: ${s.get('pnl', 0):.2f} (Held {s.get('days_held', 0)} days, Exit: {s.get('exit_reason', 'UNKNOWN')})")
