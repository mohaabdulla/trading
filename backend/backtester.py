import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import numpy as np

# Use the same universe as the screener
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", 
    "NFLX", "CRM", "INTC", "CSCO", "PEP", "AVGO", "TXN", "QCOM",
    "SOFI", "PLTR", "NIO", "PLUG", "HOOD", "AMC", "RIVN", "LCID",
    "MARA", "RIOT", "F", "SNAP", "PINS", "DKNG", "CCL", "AAL"
]

def run_backtest(initial_capital: float = 100.0, start_date="2020-01-01"):
    print("Downloading SPY market data...")
    try:
        spy_df = yf.download("SPY", start="2020-01-01", end=datetime.datetime.now().strftime('%Y-%m-%d'), progress=False)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        spy_df['SMA_50'] = spy_df['Close'].rolling(window=50).mean()
    except Exception as e:
        print(f"Failed to get SPY data: {e}")
        spy_df = pd.DataFrame()
        
    print("Downloading historical data since 2020-01-01...")
    
    # Download all tickers at once to save time
    try:
        data = yf.download(TICKERS, start="2020-01-01", end=datetime.datetime.now().strftime('%Y-%m-%d'), progress=False)
    except Exception as e:
        print(f"Error downloading data: {e}")
        return []

    processed_data = {}
    all_dates = set()

    print("Calculating technical indicators...")
    for ticker in TICKERS:
        try:
            if len(TICKERS) == 1:
                df = data.copy()
            else:
                df = data[ticker].copy()
            
            df.dropna(inplace=True)
            if len(df) < 200:
                continue
                
            # 1. MACD
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            # 2. SuperTrend
            df.ta.supertrend(length=10, multiplier=3, append=True)
            # 3. RSI
            df.ta.rsi(length=14, append=True)
            
            # Calculate 20-day rolling volume average
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
            
            df.dropna(subset=['MACD_12_26_9', 'SUPERTd_10_3', 'RSI_14', 'Vol_Avg'], inplace=True)
            processed_data[ticker] = df
            all_dates.update(df.index)
        except Exception as e:
            continue

    sorted_dates = sorted(list(all_dates))
    
    cash = initial_capital
    open_positions = []
    trade_history = []
    
    print("Simulating trades day-by-day...")
    for current_date in sorted_dates:
        # 1. Check open positions for EXIT signals
        positions_to_close = []
        for pos in open_positions:
            ticker = pos['symbol']
            if ticker in processed_data and current_date in processed_data[ticker].index:
                row = processed_data[ticker].loc[current_date]
                current_price = float(row['Close'])
                supertrend_dir = float(row['SUPERTd_10_3'])
                macd_line = float(row['MACD_12_26_9'])
                macd_signal = float(row['MACDs_12_26_9'])
                
                # Fast Exit Logic: MACD Crosses Down OR SuperTrend Flips Bearish
                if macd_line < macd_signal or supertrend_dir != 1:
                    sell_value = pos['quantity'] * current_price
                    realized_pnl = sell_value - pos['cost_basis']
                    cash += sell_value
                    
                    trade_history.append({
                        "symbol": ticker,
                        "action": "SELL",
                        "quantity": pos['quantity'],
                        "price": round(current_price, 2),
                        "timestamp": current_date.isoformat() + "Z",
                        "realized_pnl": round(realized_pnl, 2),
                        "commission": 1.00 # Simulated $1 IBKR commission
                    })
                    cash -= 1.00 # Deduct commission
                    positions_to_close.append(pos)
                    
        for pos in positions_to_close:
            open_positions.remove(pos)
            
        market_ok = True
        if not spy_df.empty and current_date in spy_df.index:
            spy_row = spy_df.loc[current_date]
            # Market Filter: Do not trade if SPY is below 50-SMA (Macro Downtrend)
            if float(spy_row['Close']) < float(spy_row['SMA_50']):
                market_ok = False
        
        # 2. Look for ENTRY signals if we have enough cash AND no open positions
        # This completely fixes the "pocket change" bug by restricting us to 1 position at a time!
        if cash >= 2.0 and len(open_positions) == 0 and market_ok:
            buy_candidates = []
            for ticker, df in processed_data.items():
                if current_date in df.index:
                    row = df.loc[current_date]
                    
                    current_price = float(row['Close'])
                    macd_line = float(row['MACD_12_26_9'])
                    macd_signal = float(row['MACDs_12_26_9'])
                    macd_hist = float(row['MACDh_12_26_9'])
                    supertrend_dir = float(row['SUPERTd_10_3'])
                    avg_vol = float(row['Vol_Avg'])
                    rsi_val = float(row['RSI_14'])
                    open_price = float(row['Open'])
                    
                    # 1. Base filters
                    if current_price < 2 or avg_vol < 2000000:
                        continue
                        
                    # 2. Macro Trend
                    # if supertrend_dir != 1:
                    #     continue
                        
                    # 3. Momentum Entry
                    if macd_line <= macd_signal:
                        continue
                        
                    # 4. Buy the Dip (Not extremely Overbought)
                    if rsi_val > 75:
                        continue
                        
                    # 5. Intraday Strength (Close > Open)
                    if current_price <= open_price:
                        continue
                        
                    buy_candidates.append({
                        "symbol": ticker,
                        "price": current_price,
                        "macd": macd_hist
                    })
            
            # Sort by MACD histogram strength
            buy_candidates.sort(key=lambda x: x['macd'], reverse=True)
            
            # Buy the top candidate we can afford
            for best_setup in buy_candidates:
                price = best_setup['price']
                
                # Invest all available cash
                quantity = int(cash // price)
                
                if quantity > 0:
                    cost_basis = quantity * price
                    cash -= cost_basis
                    
                    trade_history.append({
                        "symbol": best_setup['symbol'],
                        "action": "BUY",
                        "quantity": quantity,
                        "price": round(price, 2),
                        "timestamp": current_date.isoformat() + "Z",
                        "realized_pnl": None,
                        "commission": 1.00
                    })
                    cash -= 1.00
                    
                    open_positions.append({
                        "symbol": best_setup['symbol'],
                        "quantity": quantity,
                        "cost_basis": cost_basis,
                        "buy_date": current_date
                    })
                    
                    # We only want to open 1 new position per day at most
                    break

    # Add currently open positions to history as "Open"
    for pos in open_positions:
        trade_history.append({
            "symbol": pos['symbol'],
            "action": "BUY (OPEN)",
            "quantity": pos['quantity'],
            "price": round(pos['cost_basis']/pos['quantity'], 2),
            "timestamp": pos['buy_date'].isoformat() + "Z",
            "realized_pnl": None,
            "commission": 1.00
        })

    # Sort history descending by timestamp for the UI
    trade_history.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Assign dummy IDs for React keys
    for i, t in enumerate(trade_history):
        t['id'] = i + 1
        
    return trade_history

if __name__ == "__main__":
    res = run_backtest(100.0)
    print(f"Backtest complete. Generated {len(res)} trades.")
