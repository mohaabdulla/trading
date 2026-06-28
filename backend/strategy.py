import pandas as pd
import pandas_ta as ta

# =============================================================================
# STRATEGY CONFIGURATION
# =============================================================================

import json
import os

# Universe Selection (Halal Only)
# Load from halal_universe.json if it exists, otherwise fallback to empty list
cache_path = os.path.join(os.path.dirname(__file__), '..', 'halal_universe.json')
TICKERS = []
if os.path.exists(cache_path):
    with open(cache_path, 'r') as f:
        data = json.load(f)
        TICKERS = [t for t, d in data.items() if d.get('compliant')]
else:
    print(f"Warning: {cache_path} not found. Run halal_screener.py first.")

# Risk Management
RISK_PCT = 0.07              # Increased to 7% (optimal point for max total return of 363%)
MAX_EXPOSURE_PCT = 1.0       # Max total account exposure
MIN_TRADE_VALUE = 0.0        # Removed minimum trade value to allow small position sizing

# Stop Loss & Exits
ATR_STOP_MULTIPLIER = 1.9    # Optimal stop (1.9x ATR) for highest total return and tight drawdown
ATR_TARGET_MULTIPLIER = 3.9  # Optimal Target (3.9x ATR) to capture full moves before exhaustion
MAX_HOLD_DAYS = 10           # Hold for 10 days to maximize total return
RSI_OVERBOUGHT = 75          # Take profit if RSI > 75

# Entry Filters
MIN_PRICE = 1.0              # Penny stock filter
MAX_PRICE = 300.0            # Increased max price to include more liquid names
MIN_AVG_VOL = 500_000        # Minimum 20-day average volume
VOL_SURGE_MULTIPLIER = 1.2   # Current vol >= 1.2x avg vol (Breakout volume)
RSI_LOWER = 70               # Breakout zone lower bound
RSI_UPPER = 85               # Breakout zone upper bound
MIN_VOLATILITY_PCT = 0.02    # Require at least 2% daily ATR

# Commission Model (IBKR Tiered)
COMMISSION_PER_SHARE = 0.0035
MIN_COMMISSION = 0.35
MAX_COMMISSION_DRAG = 0.15   # Allow commission drag up to 15% for small accounts


# =============================================================================
# SHARED LOGIC
# =============================================================================

def calc_commission(shares: int) -> float:
    """Realistic IBKR tiered commission model."""
    return round(max(MIN_COMMISSION, shares * COMMISSION_PER_SHARE), 2)

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates all necessary technical indicators for the strategy."""
    df = df.copy()
    if len(df) < 60: # Need history for 50 EMA
        return pd.DataFrame()
        
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['EMA_50_past'] = df['EMA_50'].shift(5) # 5 days ago for trend slope
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df['MACDh_past'] = df['MACDh_12_26_9'].shift(1)
    df.ta.rsi(length=14, append=True)
    df.ta.atr(length=14, append=True)
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    
    # Drop rows with NaNs to ensure we don't return invalid signals
    df.dropna(subset=['EMA_20', 'EMA_50', 'EMA_200', 'MACD_12_26_9', 'RSI_14', 'ATRr_14', 'Vol_Avg'], inplace=True)
    return df

def is_buy_signal(row: pd.Series) -> bool:
    """
    Unified entry logic used by both screener and backtester.
    Evaluates a single day's data (row).
    """
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
        
        # 1. Price & Liquidity
        if not (MIN_PRICE <= current_price <= MAX_PRICE): return False
        if avg_vol < MIN_AVG_VOL: return False
        
        # 2. Trend Alignment
        if not (ema_20 > ema_50 > ema_200): return False
        if current_price <= ema_20: return False # Price must be above the short-term trend
        if ema_50 <= ema_50_past: return False
        
        # 3. Momentum Breakout Zone
        if not (RSI_LOWER <= rsi_val <= RSI_UPPER): return False
        
        # 4. MACD Rising
        macd_hist = float(row['MACDh_12_26_9'])
        macd_hist_past = float(row['MACDh_past'])
        if macd_hist <= macd_hist_past: return False # MACD histogram must be expanding
        
        # 5. Volume Surge
        if current_vol < (avg_vol * VOL_SURGE_MULTIPLIER): return False
        
        # 6. Volatility Check
        if atr_val <= 0 or (atr_val / current_price) < MIN_VOLATILITY_PCT: return False
        
        return True
    except Exception:
        return False
