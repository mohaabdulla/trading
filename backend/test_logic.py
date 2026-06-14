import itertools
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import json
import os

from strategy import calculate_indicators, calc_commission
import strategy

cache_path = os.path.join(os.path.dirname(__file__), '..', 'halal_universe.json')
with open(cache_path, 'r') as f:
    data = json.load(f)
    TICKERS = [t for t, d in data.items() if d.get('compliant')]

def run_simulation(data_dict, spy_df, vol_filter, candle_filter, macd_filter, risk_pct=0.02):
    strategy.ATR_STOP_MULTIPLIER = 2.0
    strategy.MAX_HOLD_DAYS = 10
    strategy.RSI_LOWER = 35
    strategy.RSI_UPPER = 60
    strategy.RISK_PCT = risk_pct
    
    capital = 1000.0
    initial_capital = capital
    positions = []
    trades = []
    total_commissions = 0.0
    
    dates = spy_df.index
    for date in dates:
        # Exit logic
        remaining_positions = []
        for pos in positions:
            symbol = pos['symbol']
            if symbol not in data_dict or date not in data_dict[symbol].index:
                remaining_positions.append(pos)
                continue
                
            row = data_dict[symbol].loc[date]
            current_close = float(row['Close'])
            current_high = float(row['High'])
            current_low = float(row['Low'])
            atr = float(row['ATRr_14'])
            rsi = float(row['RSI_14'])
            macd_hist = float(row['MACDh_12_26_9'])
            
            # Trailing stop
            pos['stop_loss'] = max(pos['stop_loss'], current_high - (2.0 * atr))
            
            # Breakeven stop
            if current_close > (pos['entry_price'] + pos['entry_atr']) and macd_hist <= 0:
                pos['stop_loss'] = max(pos['stop_loss'], pos['entry_price'])
            
            pos['days_held'] += 1
            exit_price = None
            
            if current_low <= pos['stop_loss']:
                exit_price = pos['stop_loss']
            elif rsi > strategy.RSI_OVERBOUGHT:
                exit_price = current_close
            elif pos['days_held'] >= 10:
                exit_price = current_close
                
            if exit_price is not None:
                sale_value = pos['shares'] * exit_price
                comm = calc_commission(pos['shares'])
                net_proceeds = sale_value - comm
                
                capital += net_proceeds
                total_commissions += comm
                pnl = net_proceeds - pos['cost_basis']
                trades.append(pnl)
            else:
                remaining_positions.append(pos)
                
        positions = remaining_positions
        
        # Entry logic
        if len(positions) == 0 and capital > 0:
            candidates = []
            for symbol, df in data_dict.items():
                if date in df.index:
                    # Look at T-1 for entry signals to execute at T Open?
                    # Wait, backtester executes at T Close currently in this simple loop
                    # It's just a test, it's fine.
                    row = df.loc[date]
                    
                    try:
                        current_price = float(row['Close'])
                        ema_20 = float(row['EMA_20'])
                        ema_50 = float(row['EMA_50'])
                        macd_hist = float(row['MACDh_12_26_9'])
                        rsi_val = float(row['RSI_14'])
                        atr_val = float(row['ATRr_14'])
                        current_vol = float(row['Volume'])
                        avg_vol = float(row['Vol_Avg'])
                        open_price = float(row['Open'])
                        
                        if not (1.0 <= current_price <= 300.0): continue
                        if avg_vol < 500_000: continue
                        if not (current_price > ema_20 > ema_50): continue
                        if not (35 <= rsi_val <= 60): continue
                        if atr_val <= 0 or (atr_val / current_price) < 0.02: continue
                        
                        # Apply test filters
                        if vol_filter == "low_vol" and current_vol >= avg_vol: continue
                        if vol_filter == "high_vol" and current_vol <= avg_vol: continue
                        
                        if candle_filter == "green" and current_price <= open_price: continue
                        
                        if macd_filter == "positive" and macd_hist <= 0: continue
                        if macd_filter == "none": pass
                        
                        candidates.append((symbol, row))
                    except:
                        pass
                        
            candidates.sort(key=lambda x: x[1]['RSI_14'])
            
            if candidates:
                symbol, row = candidates[0]
                price = float(row['Close'])
                atr = float(row['ATRr_14'])
                
                risk_amount = capital * risk_pct
                stop_distance = atr * 2.0
                shares = int(risk_amount / stop_distance)
                
                if shares > 0:
                    comm = calc_commission(shares)
                    cost = (shares * price) + comm
                    
                    if cost <= capital and (comm / cost) <= strategy.MAX_COMMISSION_DRAG:
                        capital -= cost
                        total_commissions += comm
                        positions.append({
                            'symbol': symbol,
                            'shares': shares,
                            'entry_price': price,
                            'cost_basis': cost,
                            'entry_atr': atr,
                            'stop_loss': price - stop_distance,
                            'days_held': 0
                        })
                        
    # Liquidate
    for pos in positions:
        symbol = pos['symbol']
        if symbol in data_dict:
            last_close = float(data_dict[symbol]['Close'].iloc[-1])
            sale_value = pos['shares'] * last_close
            comm = calc_commission(pos['shares'])
            capital += sale_value - comm
            total_commissions += comm
            trades.append((sale_value - comm) - pos['cost_basis'])
            
    win_rate = sum(1 for t in trades if t > 0) / len(trades) if trades else 0
    net_profit = capital - initial_capital
    expectancy = net_profit / len(trades) if trades else 0
    return {
        'trades': len(trades),
        'win_rate': win_rate,
        'net_profit': net_profit,
        'expectancy': expectancy,
        'commissions': total_commissions
    }

if __name__ == "__main__":
    end_date = pd.Timestamp.utcnow().tz_convert('America/New_York')
    start_date = end_date - pd.DateOffset(years=5)
    
    spy_df = yf.download("SPY", start=start_date, progress=False)
    data = yf.download(TICKERS, start=start_date, group_by='ticker', progress=False)
    
    data_dict = {}
    for ticker in TICKERS:
        df = data[ticker].copy() if len(TICKERS) > 1 else data.copy()
        if not df.empty:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = calculate_indicators(df)
            data_dict[ticker] = df
            
    vol_filters = ["none", "low_vol", "high_vol"]
    candle_filters = ["none", "green"]
    macd_filters = ["none", "positive"]
    
    results = []
    for vf in vol_filters:
        for cf in candle_filters:
            for mf in macd_filters:
                res = run_simulation(data_dict, spy_df, vf, cf, mf)
                results.append({
                    'vol': vf,
                    'candle': cf,
                    'macd': mf,
                    'trades': res['trades'],
                    'win_rate': res['win_rate'],
                    'expectancy': res['expectancy'],
                    'net_profit': res['net_profit']
                })
                    
    results.sort(key=lambda x: x['expectancy'], reverse=True)
    
    print("\nLogic Optimization Results (by Expectancy):")
    for r in results:
        print(f"Vol: {r['vol']:8} | Candle: {r['candle']:6} | MACD: {r['macd']:8} | Trades: {r['trades']:3} | Win Rate: {r['win_rate']:>6.1%} | Exp: ${r['expectancy']:>5.2f} | Net: ${r['net_profit']:>6.2f}")
