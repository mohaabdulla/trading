import yfinance as yf
import pandas as pd
from strategy import (
    TICKERS, MIN_TRADE_VALUE, ATR_STOP_MULTIPLIER, RISK_PCT, 
    MAX_COMMISSION_DRAG, calc_commission, calculate_indicators, is_buy_signal
)

def run_screener(capital: float = 100.0):
    """
    EMA Momentum Pullback Screener (Unified Logic)
    """
    print(f"Running EMA Momentum Pullback screener with ${capital} capital...")
    filtered_stocks = []

    # ── 1. Market Regime Filter (SPY) ──
    try:
        spy_df = yf.download("SPY", period="6mo", progress=False)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        spy_df['SMA_50'] = spy_df['Close'].rolling(window=50).mean()
        spy_latest = spy_df.iloc[-1]

        if float(spy_latest['Close']) <= float(spy_latest['SMA_50']):
            print("[X] Market regime BEARISH (SPY <= 50 SMA). No buy signals.")
            return []
        else:
            print("[OK] Market regime BULLISH (SPY > 50 SMA). Scanning...")
    except Exception as e:
        print(f"[!] Failed to check SPY market filter: {e}. Proceeding anyway.")

    # ── 2. Download data for all tickers ──
    try:
        data = yf.download(TICKERS, period="1y", group_by="ticker", auto_adjust=True, progress=False)
    except Exception as e:
        print(f"Error downloading data: {e}")
        return []

    for ticker in TICKERS:
        try:
            # Handle both single and multi-ticker yfinance output
            if len(TICKERS) == 1:
                df = data.copy()
            else:
                df = data[ticker].copy()

            df = calculate_indicators(df)
            if df.empty:
                continue

            latest = df.iloc[-1]

            # ── Apply Unified Filters ──
            if not is_buy_signal(latest):
                continue

            current_price = float(latest['Close'])
            atr_val = float(latest['ATRr_14'])
            
            # ── Position Sizing (Fixed Fractional Risk) ──
            dollar_risk = capital * RISK_PCT
            stop_distance = atr_val * ATR_STOP_MULTIPLIER
            stop_loss_price = round(current_price - stop_distance, 2)
            
            # shares = risk / stop_distance
            suggested_shares = int(dollar_risk / stop_distance)

            if suggested_shares <= 0:
                continue

            total_cost = suggested_shares * current_price
            
            # Hard constraint: Cannot exceed available cash (no margin)
            if total_cost > capital:
                suggested_shares = int(capital // current_price)
                if suggested_shares <= 0:
                    continue
                total_cost = suggested_shares * current_price

            # Skip if trade is too small
            if total_cost < MIN_TRADE_VALUE:
                continue

            # Skip if commissions are too high relative to cost
            round_trip_comm = calc_commission(suggested_shares) * 2
            if round_trip_comm / total_cost > MAX_COMMISSION_DRAG:
                continue

            filtered_stocks.append({
                "symbol": ticker,
                "price": round(current_price, 2),
                "ema_20": round(float(latest['EMA_20']), 2),
                "ema_50": round(float(latest['EMA_50']), 2),
                "rsi": round(float(latest['RSI_14']), 1),
                "macd": round(float(latest['MACDh_12_26_9']), 4),
                "atr": round(atr_val, 2),
                "volume": round(float(latest['Volume'])),
                "avg_volume": round(float(latest['Vol_Avg'])),
                "volume_ratio": round(float(latest['Volume']) / float(latest['Vol_Avg']), 2),
                "supertrend": "Bullish",
                "stop_loss": stop_loss_price,
                "risk_per_share": round(stop_distance, 2),
                "suggested_shares": suggested_shares,
                "total_investment": round(total_cost, 2),
                "risk_amount": round(suggested_shares * stop_distance, 2),
            })

        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue

    # Sort by RSI ascending (best pullback opportunities first)
    filtered_stocks.sort(key=lambda x: x['rsi'])
    
    print(f"Found {len(filtered_stocks)} stocks matching EMA Momentum Pullback criteria.")
    return filtered_stocks

if __name__ == "__main__":
    print("=" * 60)
    print("EMA Momentum Pullback Screener")
    print("=" * 60)
    results = run_screener(100.0) # Default test for small $100 account
    print(f"\nFound {len(results)} stocks matching criteria.\n")
    for r in results:
        print(f"  {r['symbol']:6s}  ${r['price']:>8.2f}  RSI={r['rsi']:>5.1f}  "
              f"MACD={r['macd']:>7.4f}  ATR=${r['atr']:>5.2f}  "
              f"Stop=${r['stop_loss']:>8.2f}  Shares={r['suggested_shares']}")
