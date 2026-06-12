import yfinance as yf
import pandas as pd
import pandas_ta as ta

# A broader universe including highly liquid small/mid-caps that are cheaper, perfect for smaller capital
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", 
    "NFLX", "CRM", "INTC", "CSCO", "PEP", "AVGO", "TXN", "QCOM",
    # Cheaper / High Liquidity stocks
    "SOFI", "PLTR", "NIO", "PLUG", "HOOD", "AMC", "RIVN", "LCID",
    "MARA", "RIOT", "F", "SNAP", "PINS", "DKNG", "CCL", "AAL"
]

def run_screener(capital: float = 1000.0):
    print(f"Running screener with ${capital} capital...")
    filtered_stocks = []
    
    # 1. Market Filter (SPY)
    try:
        spy_df = yf.download("SPY", period="6mo", progress=False)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        spy_df['SMA_50'] = spy_df['Close'].rolling(window=50).mean()
        spy_latest = spy_df.iloc[-1]
        
        if float(spy_latest['Close']) < float(spy_latest['SMA_50']):
            print("Market is in a downtrend (SPY < 50 SMA). Screener returns 0 stocks.")
            return []
    except Exception as e:
        print(f"Failed to check SPY market filter: {e}")

    # Download data for all tickers for the last 1 year
    try:
        data = yf.download(TICKERS, period="1y", group_by="ticker", auto_adjust=True, progress=False)
    except Exception as e:
        print(f"Error downloading data: {e}")
        return []

    for ticker in TICKERS:
        try:
            # Handle both single ticker and multi-ticker yfinance output formats
            if len(TICKERS) == 1:
                df = data.copy()
            else:
                df = data[ticker].copy()
            
            df.dropna(inplace=True)
            if len(df) < 200:
                continue # Not enough data for 200 SMA
            
            # Calculate Indicators using pandas_ta
            # 1. MACD
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            # 2. SuperTrend (Length=10, Multiplier=3)
            df.ta.supertrend(length=10, multiplier=3, append=True)
            # 3. RSI
            df.ta.rsi(length=14, append=True)
            # 4. Volume SMA
            df['Vol_Avg'] = df['Volume'].rolling(20).mean()
            
            # Get the latest values
            latest = df.iloc[-1]
            
            # Dropna and get values safely
            if pd.isna(latest.get('MACD_12_26_9')) or pd.isna(latest.get('SUPERTd_10_3')):
                continue
                
            current_price = float(latest['Close'])
            macd_line = float(latest['MACD_12_26_9'])
            macd_signal = float(latest['MACDs_12_26_9'])
            macd_hist = float(latest['MACDh_12_26_9'])
            supertrend_dir = float(latest['SUPERTd_10_3'])
            avg_vol = float(latest['Vol_Avg'])
            rsi_val = float(latest.get('RSI_14', 50))
            open_price = float(latest['Open'])
            
            # Base logic filters
            if current_price < 2 or avg_vol < 2000000:
                continue
                
            if supertrend_dir != 1:
                continue
                
            # 4. MACD must be positive momentum (MACD line > Signal line)
            if macd_line <= macd_signal:
                continue
                
            # 5. Buy the Dip
            if rsi_val > 75:
                continue
                
            # 6. Intraday Strength
            if current_price <= open_price:
                continue
                
            # Position Sizing: Use user's capital
            suggested_shares = int(capital // current_price)
            if suggested_shares <= 0:
                continue # Can't even afford 1 share with available capital
                
            filtered_stocks.append({
                "symbol": ticker,
                "price": round(current_price, 2),
                "volume": avg_vol,
                "macd": round(macd_hist, 3),
                "supertrend": "Bullish",
                "suggested_shares": suggested_shares,
                "total_investment": round(suggested_shares * current_price, 2)
            })

        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue

    # Sort by MACD histogram strength (strongest momentum first)
    return sorted(filtered_stocks, key=lambda x: x['macd'], reverse=True)

if __name__ == "__main__":
    print("Running screener with $1000 capital...")
    results = run_screener(1000.0)
    print(f"Found {len(results)} stocks matching criteria.")
    for r in results:
        print(r)
