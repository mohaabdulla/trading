"""
Systematic stock-specific grid search to find optimal parameters for EACH stock.
Outputs optimal_params.json
"""
import sys
import os
sys.path.insert(0, r'c:\Users\mohamed redha\Desktop\trading\backend')

import yfinance as yf
import pandas as pd
import numpy as np
import json
import itertools

cache_path = r'c:\Users\mohamed redha\Desktop\trading\halal_universe.json'
with open(cache_path, 'r') as f:
    udata = json.load(f)
    TICKERS = [t for t, d in udata.items() if d.get('compliant')]

from strategy import calculate_indicators

print(f"Tickers to optimize: {TICKERS}")
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

def simulate_single_stock(ticker, df, atr_stop, atr_target, max_hold, rsi_ob, vol_surge, min_vol_pct):
    """Simulates trading a single stock to find its optimal parameters."""
    cash = 1000.0
    initial_capital = cash
    unsettled_cash = 0.0
    open_positions = []
    
    # We simulate starting with $1000 and compounding 100% of equity on each trade 
    # to find the pure un-leveraged growth potential of the system on this ticker.
    # Risk management (sizing) will still be handled at the portfolio level later.
    
    for i, current_date in enumerate(sorted_dates):
        cash += unsettled_cash
        unsettled_cash = 0.0
        
        # Check exits
        positions_to_close = []
        for pos in open_positions:
            if current_date not in df.index:
                pos['days_held'] += 1
                continue
            row = df.loc[current_date]
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
                unsettled_cash += sell_value
                positions_to_close.append(pos)

        for pos in positions_to_close:
            open_positions.remove(pos)

        # Check entries
        market_ok = True
        if not spy_df.empty and current_date in spy_df.index:
            spy_row = spy_df.loc[current_date]
            if float(spy_row['Close']) <= float(spy_row['SMA_50']):
                market_ok = False

        if market_ok and len(open_positions) == 0 and cash > 0 and current_date in df.index:
            row = df.loc[current_date]
            try:
                cp = float(row['Close'])
                ema20 = float(row['EMA_20']); ema50 = float(row['EMA_50'])
                ema200 = float(row['EMA_200']); ema50p = float(row['EMA_50_past'])
                rsi = float(row['RSI_14']); atr = float(row['ATRr_14'])
                vol = float(row['Volume']); avgvol = float(row['Vol_Avg'])
                mh = float(row['MACDh_12_26_9']); mhp = float(row['MACDh_past'])

                if (1.0 <= cp <= 3000.0) and (avgvol >= 500_000) and (ema20 > ema50 > ema200) and \
                   (cp > ema20) and (ema50 > ema50p) and (68 <= rsi <= 85) and (mh > mhp) and \
                   (vol >= avgvol * vol_surge) and (atr > 0 and (atr / cp) >= min_vol_pct):
                    
                    stop_dist = atr * atr_stop
                    # Buy as much as possible
                    quantity = int(cash // cp)
                    if quantity > 0:
                        cost = quantity * cp
                        cash -= cost
                        open_positions.append({
                            'symbol': ticker, 'quantity': quantity,
                            'entry_price': cp, 'trailing_stop': cp - stop_dist,
                            'days_held': 0, 'atr_at_entry': atr, 'breakeven_active': False
                        })
            except Exception:
                pass

    final_value = cash + unsettled_cash
    for pos in open_positions:
        final_value += pos['quantity'] * pos['entry_price']
        
    return final_value

print("\n" + "=" * 60)
print("STOCK-SPECIFIC OPTIMIZATION")
print("=" * 60)

# Fast grid for immediate results
atr_stops = [1.5, 2.0, 2.5]
atr_targets = [4.0, 5.0, 6.0]
max_holds = [12]
rsi_obs = [70, 75]
vol_surges = [1.2]
min_vol_pcts = [0.010]

optimal_params = {}

for ticker in TICKERS:
    if ticker not in processed_data:
        continue
    print(f"\nOptimizing {ticker}...")
    df = processed_data[ticker]
    
    best_value = 0
    best_params = None
    
    for ast in atr_stops:
        for at in atr_targets:
            for mh in max_holds:
                for rob in rsi_obs:
                    for vs in vol_surges:
                        for mvp in min_vol_pcts:
                            fv = simulate_single_stock(ticker, df, ast, at, mh, rob, vs, mvp)
                            if fv > best_value:
                                best_value = fv
                                best_params = {
                                    "ATR_STOP_MULTIPLIER": ast,
                                    "ATR_TARGET_MULTIPLIER": at,
                                    "MAX_HOLD_DAYS": mh,
                                    "RSI_OVERBOUGHT": rob,
                                    "VOL_SURGE_MULTIPLIER": vs,
                                    "MIN_VOLATILITY_PCT": mvp
                                }
    
    # If the stock never made a profitable trade (value <= 1000), fall back to safe defaults
    if best_value <= 1000.0:
        print(f"  {ticker} had no profitable edge. Using safe defaults.")
        best_params = {
            "ATR_STOP_MULTIPLIER": 2.0,
            "ATR_TARGET_MULTIPLIER": 4.0,
            "MAX_HOLD_DAYS": 12,
            "RSI_OVERBOUGHT": 70,
            "VOL_SURGE_MULTIPLIER": 1.2,
            "MIN_VOLATILITY_PCT": 0.010
        }
    else:
        print(f"  Best Final Value: ${best_value:.2f}")
        print(f"  Params: {best_params}")
        
    optimal_params[ticker] = best_params

# Save the optimal parameters
out_path = os.path.join(r'c:\Users\mohamed redha\Desktop\trading', 'optimal_params.json')
with open(out_path, 'w') as f:
    json.dump(optimal_params, f, indent=4)
print(f"\nSaved optimal parameters to {out_path}")
