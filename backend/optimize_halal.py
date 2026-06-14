import itertools
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import json
import os

from strategy import calculate_indicators, is_buy_signal, calc_commission
import strategy

cache_path = os.path.join(os.path.dirname(__file__), '..', 'halal_universe.json')
with open(cache_path, 'r') as f:
    data = json.load(f)
    TICKERS = [t for t, d in data.items() if d.get('compliant')]

def run_simulation(data_dict, spy_df, atr_mult, max_hold, rsi_bounds, risk_pct=0.02):
    # Temporarily override strategy variables
    strategy.ATR_STOP_MULTIPLIER = atr_mult
    strategy.MAX_HOLD_DAYS = max_hold
    strategy.RSI_LOWER = rsi_bounds[0]
    strategy.RSI_UPPER = rsi_bounds[1]
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
            
            # Trailing stop update
            pos['stop_loss'] = max(pos['stop_loss'], current_high - (atr_mult * atr))
            
            # Breakeven stop logic
            if current_close > (pos['entry_price'] + pos['entry_atr']) and macd_hist <= 0:
                pos['stop_loss'] = max(pos['stop_loss'], pos['entry_price'])
            
            pos['days_held'] += 1
            exit_price = None
            exit_reason = ""
            
            if current_low <= pos['stop_loss']:
                exit_price = pos['stop_loss']
                exit_reason = "Stop Hit"
            elif rsi > strategy.RSI_OVERBOUGHT:
                exit_price = current_close
                exit_reason = "RSI Overbought"
            elif pos['days_held'] >= max_hold:
                exit_price = current_close
                exit_reason = "Time Stop"
                
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
                    row = df.loc[date]
                    if is_buy_signal(row):
                        candidates.append((symbol, row))
                        
            # Sort by RSI ascending (buy deepest pullback)
            candidates.sort(key=lambda x: x[1]['RSI_14'])
            
            if candidates:
                symbol, row = candidates[0]
                price = float(row['Close'])
                atr = float(row['ATRr_14'])
                
                risk_amount = capital * risk_pct
                stop_distance = atr * atr_mult
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
    
    print("Downloading data...")
    spy_df = yf.download("SPY", start=start_date, progress=False)
    data = yf.download(TICKERS, start=start_date, group_by='ticker', progress=False)
    
    data_dict = {}
    for ticker in TICKERS:
        df = data[ticker].copy() if len(TICKERS) > 1 else data.copy()
        if not df.empty:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = calculate_indicators(df)
            data_dict[ticker] = df
            
    # Parameters to test
    atr_mults = [1.5, 2.0, 2.5]
    max_holds = [3, 5, 8, 12]
    rsi_bounds_list = [(35, 60), (40, 60), (40, 65)]
    
    results = []
    print("Running optimization...")
    for atr in atr_mults:
        for hold in max_holds:
            for rsi_b in rsi_bounds_list:
                res = run_simulation(data_dict, spy_df, atr, hold, rsi_b)
                if res['trades'] > 20: # Ensure some statistical significance
                    results.append({
                        'atr': atr,
                        'hold': hold,
                        'rsi': rsi_b,
                        'trades': res['trades'],
                        'win_rate': res['win_rate'],
                        'expectancy': res['expectancy'],
                        'net_profit': res['net_profit']
                    })
                    
    results.sort(key=lambda x: x['expectancy'], reverse=True)
    
    print("\nTop 5 Parameter Sets (by Net Expectancy):")
    for r in results[:5]:
        print(f"ATR: {r['atr']}, Hold: {r['hold']}, RSI: {r['rsi']} | Trades: {r['trades']} | Win Rate: {r['win_rate']:.1%} | Exp: ${r['expectancy']:.2f} | Net Profit: ${r['net_profit']:.2f}")
