import sys
import strategy
from backtester import run_backtest

def evaluate_params(stop_mult, rsi_lower, rsi_upper, max_hold, trend_200):
    # Override strategy
    strategy.ATR_STOP_MULTIPLIER = stop_mult
    strategy.RSI_LOWER = rsi_lower
    strategy.RSI_UPPER = rsi_upper
    strategy.MAX_HOLD_DAYS = max_hold
    
    # Store old logic to restore later
    old_is_buy = strategy.is_buy_signal
    old_calc = strategy.calculate_indicators
    
    def new_calc(df):
        df = df.copy()
        if len(df) < 200: return pd.DataFrame()
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['EMA_50_past'] = df['EMA_50'].shift(5)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        df.dropna(inplace=True)
        return df
        
    def new_buy(row):
        try:
            current_price = float(row['Close'])
            ema_20 = float(row['EMA_20'])
            ema_50 = float(row['EMA_50'])
            ema_200 = float(row['EMA_200'])
            ema_50_past = float(row['EMA_50_past'])
            rsi_val = float(row['RSI_14'])
            atr_val = float(row['ATRr_14'])
            current_vol = float(row['Volume'])
            avg_vol = float(row['Vol_Avg'])
            
            if not (1.0 <= current_price <= 300.0): return False
            if avg_vol < 500_000: return False
            
            if trend_200:
                if not (current_price > ema_20 > ema_50 > ema_200): return False
            else:
                if not (current_price > ema_20 > ema_50): return False
                
            if ema_50 <= ema_50_past: return False
            if not (strategy.RSI_LOWER <= rsi_val <= strategy.RSI_UPPER): return False
            if current_vol > avg_vol: return False
            if atr_val <= 0 or (atr_val / current_price) < 0.02: return False
            
            return True
        except:
            return False

    strategy.calculate_indicators = new_calc
    strategy.is_buy_signal = new_buy
    
    # Run backtest with True (Time Stop)
    res = run_backtest(1000.0, start_date="2020-01-01", use_time_stop=True, zero_commission=False)
    
    # Restore
    strategy.calculate_indicators = old_calc
    strategy.is_buy_signal = old_is_buy
    
    return res['metrics']

if __name__ == "__main__":
    import pandas as pd
    stops = [1.5, 1.8, 2.0]
    rsis = [(35, 60), (40, 60)]
    holds = [5, 8, 10, 15]
    trends = [True, False]
    
    best_pf = 0
    best_params = None
    
    # Suppress print inside run_backtest
    import builtins
    old_print = builtins.print
    builtins.print = lambda *args, **kwargs: None
    
    for s in stops:
        for r_l, r_u in rsis:
            for h in holds:
                for t in trends:
                    m = evaluate_params(s, r_l, r_u, h, t)
                    if m['closed_trades'] >= 20:
                        pf = m['profit_factor']
                        if pf > best_pf:
                            best_pf = pf
                            best_params = (s, r_l, r_u, h, t)
    
    builtins.print = old_print
    print(f"Best PF: {best_pf} | Params: Stop={best_params[0]}, RSI={best_params[1]}-{best_params[2]}, Hold={best_params[3]}, Trend200={best_params[4]}")
