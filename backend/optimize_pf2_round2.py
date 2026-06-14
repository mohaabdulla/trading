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

def run_simulation(data_dict, spy_df, atr_stop, atr_target, rsi_lower, candle, risk_pct=0.02):
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
            
            exit_price = None
            
            if current_high >= pos['target_price']:
                exit_price = pos['target_price']
            elif current_low <= pos['stop_loss']:
                exit_price = pos['stop_loss']
                
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
                    try:
                        current_price = float(row['Close'])
                        open_price = float(row['Open'])
                        ema_20 = float(row['EMA_20'])
                        ema_50 = float(row['EMA_50'])
                        ema_200 = float(row['EMA_200'])
                        ema_50_past = float(row['EMA_50_past'])
                        rsi_val = float(row['RSI_14'])
                        atr_val = float(row['ATRr_14'])
                        current_vol = float(row['Volume'])
                        avg_vol = float(row['Vol_Avg'])
                        
                        if not (1.0 <= current_price <= 300.0): continue
                        if avg_vol < 500_000: continue
                        
                        # Strict Trend
                        if not (current_price > ema_20 > ema_50 > ema_200): continue
                        if ema_50 <= ema_50_past: continue
                            
                        # Pullback
                        if not (rsi_lower <= rsi_val <= 60): continue
                        
                        # Candle
                        if candle == "green" and current_price <= open_price: continue
                        
                        candidates.append((symbol, row))
                    except:
                        pass
                        
            candidates.sort(key=lambda x: x[1]['RSI_14'])
            
            if candidates:
                symbol, row = candidates[0]
                price = float(row['Close'])
                atr = float(row['ATRr_14'])
                
                risk_amount = capital * risk_pct
                stop_distance = atr * atr_stop
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
                            'stop_loss': price - stop_distance,
                            'target_price': price + (atr * atr_target)
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
    
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    pf = gross_profit / (gross_loss + total_commissions) if (gross_loss + total_commissions) > 0 else 0
    
    return {'trades': len(trades), 'win_rate': win_rate, 'pf': pf}

if __name__ == "__main__":
    def calc_inds(df):
        df = df.copy()
        if len(df) < 200: return pd.DataFrame()
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['EMA_50_past'] = df['EMA_50'].shift(5)
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        df.dropna(inplace=True)
        return df

    end_date = pd.Timestamp.utcnow().tz_convert('America/New_York')
    start_date = end_date - pd.DateOffset(years=5)
    spy_df = yf.download("SPY", start=start_date, progress=False)
    data = yf.download(TICKERS, start=start_date, group_by='ticker', progress=False)
    
    data_dict = {}
    for ticker in TICKERS:
        df = data[ticker].copy() if len(TICKERS) > 1 else data.copy()
        if not df.empty:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = calc_inds(df)
            data_dict[ticker] = df
            
    atr_stops = [1.0, 1.5]
    atr_targets = [3.0, 4.0, 5.0, 6.0, 8.0]
    candles = ["none", "green"]
    
    results = []
    print("Running PF=2.0 Optimizer (Round 2)...")
    for s in atr_stops:
        for t in atr_targets:
            for c in candles:
                res = run_simulation(data_dict, spy_df, s, t, 40, c)
                if res['trades'] >= 10:
                    results.append({
                        'stop': s, 'target': t, 'candle': c,
                        'pf': res['pf'], 'trades': res['trades'], 'wr': res['win_rate']
                    })
                        
    results.sort(key=lambda x: x['pf'], reverse=True)
    for r in results[:10]:
        print(f"Stop: {r['stop']} | Target: {r['target']} | Candle: {r['candle']:5} -> PF: {r['pf']:.2f} | Trades: {r['trades']} | WR: {r['wr']:.1%}")
