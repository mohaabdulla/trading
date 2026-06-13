import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# Focused universe: affordable, volatile, high-liquidity stocks suited for $1,000 accounts
TICKERS = [
    # Tech (affordable & liquid)
    "SOFI", "PLTR", "HOOD", "SNAP", "PINS", "DKNG", "U",
    # EV & Energy
    "F", "RIVN", "LCID", "NIO", "PLUG", "FCEL",
    # Crypto-adjacent
    "MARA", "RIOT", "COIN",
    # Consumer & Travel
    "CCL", "AAL", "DAL", "NCLH",
    # Biotech (volatile)
    "DNA", "CRSP", "BEAM",
    # Mid-cap value (diversification)
    "AMD", "INTC", "CSCO", "T", "UBER",
]

# Risk management constants
ATR_STOP_MULTIPLIER = 2.0  # Stop loss = 2x ATR below entry
MIN_TRADE_VALUE = 25.0     # Don't trade if total cost < $25


def _calc_commission(shares):
    """Realistic IBKR tiered commission: $0.0035/share, $0.35 minimum."""
    return round(max(0.35, shares * 0.0035), 2)


def _get_risk_pct(capital):
    """Adaptive risk % based on account size."""
    if capital < 500:
        return 0.05    # 5% risk for tiny accounts
    elif capital < 2000:
        return 0.03    # 3% risk for small accounts
    else:
        return 0.02    # 2% risk for normal accounts


def run_screener(capital: float = 1000.0):
    """
    EMA Momentum Pullback Screener
    
    Strategy logic:
    1. Market filter: SPY must be above its 50-day SMA (bull market regime)
    2. Trend: Price > EMA 20, and EMA 20 > EMA 50 (bullish alignment)
    3. Pullback zone: RSI between 40-65 (not overbought, buying the dip)
    4. Momentum: MACD histogram > 0 (positive momentum confirmed)
    5. Volume: Current volume > 1.5x 20-day average (institutional interest)
    6. Position sizing: ATR-based with 2% risk rule
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

        if float(spy_latest['Close']) < float(spy_latest['SMA_50']):
            print("[X] Market regime BEARISH (SPY < 50 SMA). No buy signals.")
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

            df.dropna(inplace=True)
            if len(df) < 60:
                continue  # Need at least 60 days for EMA 50

            # ── Calculate Indicators ──
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.atr(length=14, append=True)
            df['Vol_Avg'] = df['Volume'].rolling(20).mean()

            latest = df.iloc[-1]

            # Safety: skip if key indicators are NaN
            if pd.isna(latest.get('MACD_12_26_9')) or pd.isna(latest.get('RSI_14')) or pd.isna(latest.get('ATRr_14')):
                continue

            current_price = float(latest['Close'])
            ema_20 = float(latest['EMA_20'])
            ema_50 = float(latest['EMA_50'])
            macd_hist = float(latest['MACDh_12_26_9'])
            rsi_val = float(latest['RSI_14'])
            atr_val = float(latest['ATRr_14'])
            current_vol = float(latest['Volume'])
            avg_vol = float(latest['Vol_Avg'])

            # ── Apply Filters ──

            # F1: Minimum price & liquidity
            if current_price < 1.0 or avg_vol < 500_000:
                continue

            # F2: Trend alignment — Price > EMA 20 > EMA 50
            if not (current_price > ema_20 > ema_50):
                continue

            # F3: RSI pullback zone (40-65) — buying the dip, not chasing
            if rsi_val < 40 or rsi_val > 65:
                continue

            # F4: MACD histogram positive (momentum confirmed)
            if macd_hist <= 0:
                continue

            # F5: Volume surge — current vol > 1.5x average
            if avg_vol > 0 and current_vol < (avg_vol * 1.5):
                continue

            # ── Position Sizing (ATR-based, adaptive risk rule) ──
            if atr_val <= 0:
                continue

            risk_pct = _get_risk_pct(capital)
            dollar_risk = capital * risk_pct
            stop_distance = atr_val * ATR_STOP_MULTIPLIER
            stop_loss_price = round(current_price - stop_distance, 2)
            suggested_shares = int(dollar_risk / stop_distance)

            if suggested_shares <= 0:
                continue

            total_cost = suggested_shares * current_price
            if total_cost > capital:
                # Reduce to what we can afford
                suggested_shares = int(capital // current_price)
                if suggested_shares <= 0:
                    continue
                total_cost = suggested_shares * current_price

            # Skip if trade is too small
            if total_cost < MIN_TRADE_VALUE:
                continue

            # Skip if round-trip commissions > 3% of trade value
            round_trip_comm = _calc_commission(suggested_shares) * 2
            if round_trip_comm / total_cost > 0.03:
                continue

            filtered_stocks.append({
                "symbol": ticker,
                "price": round(current_price, 2),
                "ema_20": round(ema_20, 2),
                "ema_50": round(ema_50, 2),
                "rsi": round(rsi_val, 1),
                "macd": round(macd_hist, 4),
                "atr": round(atr_val, 2),
                "volume": round(current_vol),
                "avg_volume": round(avg_vol),
                "volume_ratio": round(current_vol / avg_vol, 2) if avg_vol > 0 else 0,
                "supertrend": "Bullish",  # Kept for UI compatibility
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
    results = run_screener(1000.0)
    print(f"\nFound {len(results)} stocks matching criteria.\n")
    for r in results:
        print(f"  {r['symbol']:6s}  ${r['price']:>8.2f}  RSI={r['rsi']:>5.1f}  "
              f"MACD={r['macd']:>7.4f}  ATR=${r['atr']:>5.2f}  "
              f"Stop=${r['stop_loss']:>8.2f}  Shares={r['suggested_shares']}")
