import backtester
import strategy
import sys
import contextlib

results = []
for hold_days in [3, 4, 5, 10, 15]:
    backtester.MAX_HOLD_DAYS = hold_days
    print(f"Running backtest for hold_days = {hold_days}...")
    res = backtester.run_backtest(initial_capital=1000.0, start_date="2020-01-01", use_time_stop=True, zero_commission=False)
    metrics = res['metrics']
    results.append({
        'hold_days': hold_days,
        'expectancy': metrics['expectancy'],
        'net_profit': metrics['net_profit'],
        'win_rate': metrics['win_rate'],
        'trades': metrics['closed_trades'],
        'total_return_pct': metrics['total_return_pct']
    })

print("\n--- RESULTS ---")
for r in results:
    print(f"Hold: {r['hold_days']} Days | Return: {r['total_return_pct']}% | Net: ${r['net_profit']} | WinRate: {r['win_rate']}% | Trades: {r['trades']}")

# The logic: "check 5 if better, if not 4, if not 3"
# We define "better" as higher expectancy or net profit. Let's use net_profit as the primary metric.
