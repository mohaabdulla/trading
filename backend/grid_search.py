"""
Systematic grid search to find optimal parameters for 500%+ return.
Downloads data ONCE, then sweeps all parameter combos.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)).replace('\\scratch', '\\..\\..\\..\\..\\Desktop\\trading\\backend'))
sys.path.insert(0, r'c:\Users\mohamed redha\Desktop\trading\backend')

import yfinance as yf
import pandas as pd
import numpy as np
import json

# Load tickers
cache_path = r'c:\Users\mohamed redha\Desktop\trading\halal_universe.json'
with open(cache_path, 'r') as f:
    udata = json.load(f)
    TICKERS = [t for t, d in udata.items() if d.get('compliant')]

# Import strategy functions
from strategy import calculate_indicators, COMMISSION_PER_SHARE, MIN_COMMISSION

print(f"Tickers: {TICKERS}")
print("Downloading data (one-time)...")
spy_df = yf.download("SPY", start="2020-01-01", progress=False)
if isinstance(spy_df.columns, pd.MultiIndex):
    spy_df.columns = spy_df.columns.get_level_values(0)
spy_df['SMA_50'] = spy_df['Close'].rolling(window=50).mean()

data = yf.download(TICKERS, start="2020-01-01", group_by='ticker', progress=False)

processed_data = {}
all_dates = set()
for ticker in TICKERS:
    try:
        if len(TICKERS) == 1:
            df = data.copy()
        else:
            df = data[ticker].copy()
        df = calculate_indicators(df)
        if not df.empty:
            processed_data[ticker] = df
            all_dates.update(df.index)
    except Exception:
        continue

sorted_dates = sorted(list(all_dates))
print(f"Data ready: {len(processed_data)} tickers, {len(sorted_dates)} trading days")


def run_fast_backtest(risk_pct, atr_stop, atr_target, max_hold, rsi_ob,
                      rsi_lower, rsi_upper, vol_surge, min_vol_pct,
                      initial_capital=1000.0):
    cash = initial_capital
    unsettled_cash = 0.0
    open_positions = []
    equity_curve = []
    pending_buy_orders = []

    for i, current_date in enumerate(sorted_dates):
        cash += unsettled_cash
        unsettled_cash = 0.0

        portfolio_value = cash
        for pos in open_positions:
            ticker = pos['symbol']
            if ticker in processed_data and current_date in processed_data[ticker].index:
                portfolio_value += pos['quantity'] * float(processed_data[ticker].loc[current_date]['Close'])
            else:
                portfolio_value += pos['quantity'] * pos['entry_price']
        equity_curve.append(portfolio_value)

        for order in pending_buy_orders:
            ticker = order['symbol']
            if ticker not in processed_data or current_date not in processed_data[ticker].index:
                continue
            row = processed_data[ticker].loc[current_date]
            open_price = float(row['Open'])
            quantity = order['shares']
            cost_basis = quantity * open_price
            buy_comm = round(max(MIN_COMMISSION, quantity * COMMISSION_PER_SHARE), 2)
            if cost_basis + buy_comm > cash:
                available = cash - buy_comm
                if available > 0:
                    quantity = int(available // open_price)
                    cost_basis = quantity * open_price
                    buy_comm = round(max(MIN_COMMISSION, quantity * COMMISSION_PER_SHARE), 2)
                else:
                    quantity = 0
            if quantity > 0 and (cost_basis + buy_comm <= cash):
                cash -= cost_basis + buy_comm
                open_positions.append({
                    'symbol': ticker, 'quantity': quantity,
                    'entry_price': open_price, 'cost_basis': cost_basis,
                    'trailing_stop': open_price - order['stop_distance'],
                    'entry_date': current_date, 'days_held': 0,
                    'atr_at_entry': order['atr'], 'breakeven_active': False,
                })
        pending_buy_orders = []

        positions_to_close = []
        for pos in open_positions:
            ticker = pos['symbol']
            if ticker not in processed_data or current_date not in processed_data[ticker].index:
                pos['days_held'] += 1
                continue
            row = processed_data[ticker].loc[current_date]
            current_price = float(row['Close'])
            high_price = float(row['High'])
            rsi_val = float(row['RSI_14'])
            atr_val = float(row['ATRr_14'])
            macd_hist = float(row['MACDh_12_26_9'])
            pos['days_held'] += 1

            if not pos.get('breakeven_active') and current_price >= pos['entry_price'] + pos['atr_at_entry'] and macd_hist <= 0:
                pos['breakeven_active'] = True
                if pos['entry_price'] > pos['trailing_stop']:
                    pos['trailing_stop'] = pos['entry_price']

            new_stop = high_price - (atr_stop * atr_val)
            if new_stop > pos['trailing_stop']:
                pos['trailing_stop'] = new_stop

            exit_reason = None
            sell_price = current_price
            target_price = pos['entry_price'] + (pos['atr_at_entry'] * atr_target)
            if high_price >= target_price:
                exit_reason = "TARGET"; sell_price = target_price
            elif current_price <= pos['trailing_stop']:
                exit_reason = "STOP"
            elif rsi_val > rsi_ob:
                exit_reason = "RSI_OB"
            elif pos['days_held'] >= max_hold:
                exit_reason = "TIME"

            if exit_reason:
                sell_value = pos['quantity'] * sell_price
                sell_comm = round(max(MIN_COMMISSION, pos['quantity'] * COMMISSION_PER_SHARE), 2)
                unsettled_cash += sell_value
                cash -= sell_comm
                positions_to_close.append(pos)

        for pos in positions_to_close:
            open_positions.remove(pos)

        market_ok = True
        if not spy_df.empty and current_date in spy_df.index:
            spy_row = spy_df.loc[current_date]
            if float(spy_row['Close']) <= float(spy_row['SMA_50']):
                market_ok = False

        if market_ok:
            held_symbols = {pos['symbol'] for pos in open_positions}
            current_equity = cash + unsettled_cash + sum(p['quantity'] * p['entry_price'] for p in open_positions)
            dollar_risk = current_equity * risk_pct
            max_total_exposure = current_equity * 1.0
            current_exposure = sum(p['quantity'] * p['entry_price'] for p in open_positions)
            remaining_exposure = max_total_exposure - current_exposure

            buy_candidates = []
            for ticker, df in processed_data.items():
                if ticker in held_symbols or current_date not in df.index:
                    continue
                row = df.loc[current_date]
                try:
                    cp = float(row['Close'])
                    ema20 = float(row['EMA_20']); ema50 = float(row['EMA_50'])
                    ema200 = float(row['EMA_200']); ema50p = float(row['EMA_50_past'])
                    rsi = float(row['RSI_14']); atr = float(row['ATRr_14'])
                    vol = float(row['Volume']); avgvol = float(row['Vol_Avg'])
                    mh = float(row['MACDh_12_26_9']); mhp = float(row['MACDh_past'])

                    if not (1.0 <= cp <= 300.0): continue
                    if avgvol < 500_000: continue
                    if not (ema20 > ema50 > ema200): continue
                    if cp <= ema20: continue
                    if ema50 <= ema50p: continue
                    if not (rsi_lower <= rsi <= rsi_upper): continue
                    if mh <= mhp: continue
                    if vol < (avgvol * vol_surge): continue
                    if atr <= 0 or (atr / cp) < min_vol_pct: continue

                    stop_dist = atr * atr_stop
                    shares = int(dollar_risk / stop_dist)
                    if shares > 0:
                        buy_candidates.append({
                            'symbol': ticker, 'close': cp, 'rsi': rsi,
                            'atr': atr, 'shares': shares, 'stop_distance': stop_dist,
                        })
                except:
                    continue

            buy_candidates.sort(key=lambda x: x['rsi'])
            projected_cash = cash + unsettled_cash
            for c in buy_candidates:
                cost = c['shares'] * c['close']
                comm = round(max(MIN_COMMISSION, c['shares'] * COMMISSION_PER_SHARE), 2)
                if cost + comm > projected_cash: continue
                if cost > remaining_exposure: continue
                if comm > 0 and (comm * 2) / cost > 0.15: continue
                pending_buy_orders.append(c)
                projected_cash -= (cost + comm)
                remaining_exposure -= cost

    final_value = cash + unsettled_cash
    for pos in open_positions:
        final_value += pos['quantity'] * pos['entry_price']
    total_return = ((final_value - initial_capital) / initial_capital) * 100

    max_dd = 0
    if equity_curve:
        peak = equity_curve[0]
        for val in equity_curve:
            if val > peak: peak = val
            dd = ((peak - val) / peak) * 100 if peak > 0 else 0
            if dd > max_dd: max_dd = dd

    return round(total_return, 2), round(max_dd, 2), round(final_value, 2)


# ============================================================================
# GRID SEARCH
# ============================================================================
print("\n" + "=" * 90)
print("GRID SEARCH - Finding optimal parameters for 500%+ return")
print("=" * 90)

# Phase 1: Core R:R sweep
risk_pcts = [0.05, 0.06, 0.07, 0.08, 0.09]
atr_stops = [1.5, 2.0, 2.5]
atr_targets = [4.0, 5.0, 6.0]

print("\n--- Phase 1: Risk/Stop/Target sweep ---")
results = []
total = len(risk_pcts) * len(atr_stops) * len(atr_targets)
count = 0
for rp in risk_pcts:
    for ast in atr_stops:
        for at in atr_targets:
            count += 1
            ret, dd, fv = run_fast_backtest(rp, ast, at, 12, 75, 68, 85, 1.2, 0.02)
            results.append((ret, dd, rp, ast, at))
            if count % 10 == 0:
                print(f"  [{count}/{total}] tested...")

results.sort(key=lambda x: x[0], reverse=True)
print(f"\nTop 10 Risk/Stop/Target combos:")
print(f"{'Return':>10} {'MaxDD':>8} {'Risk%':>7} {'ATR_Stop':>10} {'ATR_Target':>12}")
print("-" * 55)
for ret, dd, rp, ast, at in results[:10]:
    print(f"{ret:>9.1f}% {dd:>7.1f}% {rp:>6.0%} {ast:>10.1f} {at:>12.1f}")

# Phase 2: Full sweep on top 3
print("\n--- Phase 2: Full sweep on top combos ---")
top3 = results[:3]

max_holds = [8, 12, 16, 20]
rsi_obs = [70, 75, 80]
rsi_lowers = [65, 68]
rsi_uppers = [85, 90]
vol_surges = [1.0, 1.1, 1.2]
min_vol_pcts = [0.015, 0.02]

full_results = []
total2 = len(top3) * len(max_holds) * len(rsi_obs) * len(rsi_lowers) * len(rsi_uppers) * len(vol_surges) * len(min_vol_pcts)
count2 = 0

for base_ret, base_dd, rp, ast, at in top3:
    for mh in max_holds:
        for rob in rsi_obs:
            for rl in rsi_lowers:
                for ru in rsi_uppers:
                    for vs in vol_surges:
                        for mvp in min_vol_pcts:
                            count2 += 1
                            ret, dd, fv = run_fast_backtest(rp, ast, at, mh, rob, rl, ru, vs, mvp)
                            full_results.append({
                                'return': ret, 'dd': dd, 'final': fv,
                                'risk': rp, 'stop': ast, 'target': at,
                                'hold': mh, 'rsi_ob': rob,
                                'rsi_l': rl, 'rsi_u': ru,
                                'vol_surge': vs, 'min_vol': mvp
                            })
                            if count2 % 100 == 0:
                                print(f"  [{count2}/{total2}] tested...")

full_results.sort(key=lambda x: x['return'], reverse=True)

print(f"\n{'='*100}")
print(f"TOP 15 PARAMETER SETS (sorted by Total Return)")
print(f"{'='*100}")
print(f"{'Return':>8} {'MaxDD':>7} {'Final':>8} {'Risk':>5} {'Stop':>5} {'Tgt':>4} {'Hold':>5} {'RSI_OB':>7} {'RSI_L':>6} {'RSI_U':>6} {'VolS':>5} {'MinV':>5}")
print("-" * 100)
for r in full_results[:15]:
    print(f"{r['return']:>7.1f}% {r['dd']:>6.1f}% ${r['final']:>7.0f} {r['risk']:>4.0%} {r['stop']:>5.1f} {r['target']:>4.1f} {r['hold']:>5} {r['rsi_ob']:>7} {r['rsi_l']:>6} {r['rsi_u']:>6} {r['vol_surge']:>5.1f} {r['min_vol']:>5.3f}")

print(f"\n{'='*100}")
print(f"BEST RESULT:")
best = full_results[0]
print(f"  Return: {best['return']}%  |  Max DD: {best['dd']}%  |  Final Value: ${best['final']}")
print(f"  RISK_PCT={best['risk']}, ATR_STOP={best['stop']}, ATR_TARGET={best['target']}")
print(f"  MAX_HOLD={best['hold']}, RSI_OB={best['rsi_ob']}, RSI_LOWER={best['rsi_l']}, RSI_UPPER={best['rsi_u']}")
print(f"  VOL_SURGE={best['vol_surge']}, MIN_VOL={best['min_vol']}")
