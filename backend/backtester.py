import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import numpy as np

# Same universe as the screener
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
ATR_STOP_MULTIPLIER = 4.0   # Disaster stop = 4x ATR
MAX_HOLD_DAYS = 1            # Force-close next day (1-day mean reversion)
MIN_TRADE_VALUE = 25.0       # Don't trade if total cost < $25


def _calc_commission(shares):
    """Realistic IBKR tiered commission: $0.0035/share, $0.35 minimum."""
    return round(max(0.35, shares * 0.0035), 2)


def _get_risk_params(capital):
    """Adaptive risk parameters based on account size."""
    if capital < 1000:
        # High risk allocation (100%) and 1 position to overcome commissions on low capital
        return 1.0, 1
    elif capital < 2000:
        return 0.03, 2    # 3% risk, 2 positions
    else:
        return 0.02, 3    # 2% risk, 3 positions


def run_backtest(initial_capital: float = 1000.0, start_date="2020-01-01"):
    """
    EMA Momentum Pullback Backtester
    
    Entry:
      - Market regime: SPY > 50 SMA
      - Trend: Price > EMA 20 > EMA 50
      - Pullback: RSI between 40-65
      - Momentum: MACD histogram > 0
      - Volume: > 1.5x 20-day average
    
    Exit (any of):
      - ATR trailing stop hit (price < trailing_stop)
      - RSI > 75 (overbought exit)
      - Held > 30 trading days (time stop)
      - Breakeven stop: after 1x ATR profit, stop moves to entry price
    
    Risk management:
      - Adaptive: 5% risk for <$500, 3% for <$2000, 2% for larger
      - Position size = risk / (2 x ATR)
      - Max positions: 1 for <$500, 2 for <$2000, 3 for larger
      - Realistic IBKR commissions ($0.0035/share, $0.35 min)
      - Skip trades where round-trip commission > 3% of trade value
    """
    print(f"Starting backtest with ${initial_capital} capital from {start_date}...")

    # ── Download SPY for market regime filter ──
    print("Downloading SPY market data...")
    try:
        spy_df = yf.download("SPY", start=start_date,
                             end=datetime.datetime.now().strftime('%Y-%m-%d'),
                             progress=False)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        spy_df['SMA_50'] = spy_df['Close'].rolling(window=50).mean()
    except Exception as e:
        print(f"Failed to get SPY data: {e}")
        spy_df = pd.DataFrame()

    # ── Download all ticker data ──
    print("Downloading historical data...")
    try:
        data = yf.download(TICKERS, start=start_date,
                           end=datetime.datetime.now().strftime('%Y-%m-%d'),
                           group_by='ticker', progress=False)
    except Exception as e:
        print(f"Error downloading data: {e}")
        return {"trades": [], "metrics": _empty_metrics(initial_capital)}

    # ── Pre-calculate indicators for every ticker ──
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

            # EMAs
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            # MACD
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            # RSI
            df.ta.rsi(length=14, append=True)
            # ATR
            df.ta.atr(length=14, append=True)
            # Volume average
            df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()

            df.dropna(subset=['EMA_20', 'EMA_50', 'EMA_200', 'MACD_12_26_9', 'RSI_14', 'ATRr_14', 'Vol_Avg'], inplace=True)

            processed_data[ticker] = df
            all_dates.update(df.index)
        except Exception as e:
            continue

    if not all_dates:
        print("No data available for any ticker.")
        return {"trades": [], "metrics": _empty_metrics(initial_capital)}

    sorted_dates = sorted(list(all_dates))

    # ── Simulation state ──
    cash = initial_capital
    risk_pct, max_positions = _get_risk_params(initial_capital)
    open_positions = []   # List of dicts with trailing_stop, breakeven_stop_active, etc.
    trade_history = []
    equity_curve = []     # Track daily equity for drawdown calc
    skipped_commission = 0  # Count trades skipped due to commission ratio

    print(f"Simulating {len(sorted_dates)} trading days across {len(processed_data)} stocks...")

    for current_date in sorted_dates:
        # ── Track equity ──
        portfolio_value = cash
        for pos in open_positions:
            ticker = pos['symbol']
            if ticker in processed_data and current_date in processed_data[ticker].index:
                row = processed_data[ticker].loc[current_date]
                portfolio_value += pos['quantity'] * float(row['Close'])
            else:
                portfolio_value += pos['quantity'] * pos['entry_price']
        equity_curve.append(portfolio_value)

        # ══════════════════════════════════════════
        # EXIT LOGIC — Check open positions
        # ══════════════════════════════════════════
        positions_to_close = []
        for pos in open_positions:
            ticker = pos['symbol']
            if ticker not in processed_data or current_date not in processed_data[ticker].index:
                pos['days_held'] += 1
                continue

            row = processed_data[ticker].loc[current_date]
            current_price = float(row['Close'])
            high_price = float(row['High'])
            rsi_val = float(row['RSI_14'])
            atr_val = float(row['ATRr_14'])
            macd_hist = float(row['MACDh_12_26_9'])

            pos['days_held'] += 1

            # Breakeven stop: after momentum is done (MACD <= 0) while in profit
            if not pos.get('breakeven_active') and current_price >= pos['entry_price'] + pos['atr_at_entry'] and macd_hist <= 0:
                pos['breakeven_active'] = True
                # Move stop to at least entry price (breakeven)
                if pos['entry_price'] > pos['trailing_stop']:
                    pos['trailing_stop'] = pos['entry_price']

            # Update trailing stop (moves UP with price, never down)
            new_stop = high_price - (ATR_STOP_MULTIPLIER * atr_val)
            if new_stop > pos['trailing_stop']:
                pos['trailing_stop'] = new_stop

            # EXIT CONDITIONS (any one triggers)
            exit_reason = None

            # E1: Trailing stop hit
            if current_price <= pos['trailing_stop']:
                exit_reason = "STOP"

            # E2: RSI overbought (take profit)
            elif rsi_val > 75:
                exit_reason = "RSI_OB"

            # E3: Time stop (held too long)
            elif pos['days_held'] >= MAX_HOLD_DAYS:
                exit_reason = "TIME"

            if exit_reason:
                sell_value = pos['quantity'] * current_price
                realized_pnl = sell_value - pos['cost_basis']
                sell_commission = _calc_commission(pos['quantity'])
                cash += sell_value
                cash -= sell_commission

                trade_history.append({
                    "symbol": ticker,
                    "action": "SELL",
                    "quantity": pos['quantity'],
                    "price": round(current_price, 2),
                    "timestamp": current_date.isoformat() + "Z",
                    "realized_pnl": round(realized_pnl, 2),
                    "commission": sell_commission,
                    "exit_reason": exit_reason,
                    "days_held": pos['days_held'],
                })
                positions_to_close.append(pos)

        for pos in positions_to_close:
            open_positions.remove(pos)

        # ══════════════════════════════════════════
        # ENTRY LOGIC — Look for new positions
        # ══════════════════════════════════════════

        # Market regime filter
        market_ok = True
        if not spy_df.empty and current_date in spy_df.index:
            spy_row = spy_df.loc[current_date]
            spy_close = float(spy_row['Close'])
            spy_sma = float(spy_row['SMA_50']) if not pd.isna(spy_row['SMA_50']) else 0
            if spy_sma > 0 and spy_close < spy_sma:
                market_ok = False

        # Recalculate risk params as capital changes
        current_equity = cash + sum(p['quantity'] * p['entry_price'] for p in open_positions)
        risk_pct, max_positions = _get_risk_params(current_equity)

        # Check if we can open more positions
        available_slots = max_positions - len(open_positions)
        held_symbols = {pos['symbol'] for pos in open_positions}

        if cash >= MIN_TRADE_VALUE and available_slots > 0 and market_ok:
            buy_candidates = []

            for ticker, df in processed_data.items():
                # Don't buy a ticker we already hold
                if ticker in held_symbols:
                    continue

                if current_date not in df.index:
                    continue

                row = df.loc[current_date]
                current_price = float(row['Close'])
                open_price = float(row['Open'])
                high_price = float(row['High'])
                low_price = float(row['Low'])
                ema_20 = float(row['EMA_20'])
                ema_50 = float(row['EMA_50'])
                ema_200 = float(row['EMA_200'])
                macd_hist = float(row['MACDh_12_26_9'])
                rsi_val = float(row['RSI_14'])
                atr_val = float(row['ATRr_14'])
                current_vol = float(row['Volume'])
                avg_vol = float(row['Vol_Avg'])

                # ── Entry filters ──

                # F1: Minimum price & liquidity (Max $30 for higher % swings)
                if current_price < 1.0 or current_price >= 30.0 or avg_vol < 500_000:
                    continue

                # F2: Trend alignment (Bull Market Dip - Must be above 50-day EMA)
                if current_price < ema_50:
                    continue

                # F3: Oversold (Mean Reversion edge)
                if rsi_val > 45:
                    continue

                # F4: Must be a red day
                if current_price >= open_price:
                    continue

                # F5: ATR valid
                if atr_val <= 0:
                    continue

                # F6: Volatility filter (Require at least 4% daily moves to beat commissions)
                vol_pct = atr_val / current_price
                if vol_pct < 0.04:
                    continue

                # Position sizing with adaptive risk rule
                dollar_risk = cash * risk_pct
                stop_distance = atr_val * ATR_STOP_MULTIPLIER
                suggested_shares = int(dollar_risk / stop_distance)

                if suggested_shares <= 0:
                    continue

                total_cost = suggested_shares * current_price
                if total_cost > cash:
                    suggested_shares = int(cash // current_price)
                    if suggested_shares <= 0:
                        continue
                    total_cost = suggested_shares * current_price

                # Skip if trade is too small
                if total_cost < MIN_TRADE_VALUE:
                    continue

                # Skip if round-trip commissions > 3% of trade value
                round_trip_comm = _calc_commission(suggested_shares) * 2
                if round_trip_comm / total_cost > 0.03:
                    skipped_commission += 1
                    continue

                buy_candidates.append({
                    "symbol": ticker,
                    "price": current_price,
                    "rsi": rsi_val,
                    "macd_hist": macd_hist,
                    "atr": atr_val,
                    "shares": suggested_shares,
                    "cost": total_cost,
                    "stop_distance": stop_distance,
                })

            # Sort by RSI ascending (deepest pullback = best opportunity)
            buy_candidates.sort(key=lambda x: x['rsi'])

            # Buy top candidates up to available slots
            for candidate in buy_candidates[:available_slots]:
                price = candidate['price']
                quantity = candidate['shares']
                cost_basis = quantity * price
                buy_commission = _calc_commission(quantity)

                if cost_basis + buy_commission > cash:
                    continue

                cash -= cost_basis
                cash -= buy_commission

                initial_stop = price - candidate['stop_distance']

                trade_history.append({
                    "symbol": candidate['symbol'],
                    "action": "BUY",
                    "quantity": quantity,
                    "price": round(price, 2),
                    "timestamp": current_date.isoformat() + "Z",
                    "realized_pnl": None,
                    "commission": buy_commission,
                    "exit_reason": None,
                    "days_held": None,
                })

                open_positions.append({
                    "symbol": candidate['symbol'],
                    "quantity": quantity,
                    "entry_price": price,
                    "cost_basis": cost_basis,
                    "trailing_stop": initial_stop,
                    "entry_date": current_date,
                    "days_held": 0,
                    "atr_at_entry": candidate['atr'],
                    "breakeven_active": False,
                })

                available_slots -= 1
                if available_slots <= 0:
                    break

    # ── Mark remaining open positions ──
    for pos in open_positions:
        trade_history.append({
            "symbol": pos['symbol'],
            "action": "BUY (OPEN)",
            "quantity": pos['quantity'],
            "price": round(pos['entry_price'], 2),
            "timestamp": pos['entry_date'].isoformat() + "Z",
            "realized_pnl": None,
            "commission": _calc_commission(pos['quantity']),
            "exit_reason": None,
            "days_held": pos['days_held'],
        })

    # ── Calculate performance metrics ──
    metrics = _calculate_metrics(trade_history, equity_curve, initial_capital, cash, open_positions)

    # Sort history descending
    trade_history.sort(key=lambda x: x['timestamp'], reverse=True)

    # Assign IDs for React keys
    for i, t in enumerate(trade_history):
        t['id'] = i + 1

    print(f"\nBacktest complete: {metrics['total_trades']} trades, "
          f"Win Rate: {metrics['win_rate']}%, "
          f"Total Return: {metrics['total_return_pct']}%, "
          f"Max Drawdown: {metrics['max_drawdown_pct']}%")

    return {"trades": trade_history, "metrics": metrics}


def _calculate_metrics(trade_history, equity_curve, initial_capital, final_cash, open_positions):
    """Calculate comprehensive backtest performance metrics."""
    sell_trades = [t for t in trade_history if t['action'] == 'SELL']
    buy_trades = [t for t in trade_history if t['action'] == 'BUY']

    wins = [t for t in sell_trades if t['realized_pnl'] and t['realized_pnl'] > 0]
    losses = [t for t in sell_trades if t['realized_pnl'] and t['realized_pnl'] <= 0]

    total_realized = sum(t['realized_pnl'] for t in sell_trades if t['realized_pnl'])
    total_commissions = sum(t['commission'] for t in trade_history if t['commission'])

    # Final portfolio value (cash + open positions at last known price)
    final_value = final_cash
    for pos in open_positions:
        final_value += pos['quantity'] * pos['entry_price']  # Conservative: use entry price

    total_return_pct = round(((final_value - initial_capital) / initial_capital) * 100, 2) if initial_capital > 0 else 0

    # Max drawdown from equity curve
    max_drawdown_pct = 0
    if equity_curve:
        peak = equity_curve[0]
        for val in equity_curve:
            if val > peak:
                peak = val
            drawdown = ((peak - val) / peak) * 100 if peak > 0 else 0
            if drawdown > max_drawdown_pct:
                max_drawdown_pct = drawdown

    # Win rate
    total_closed = len(sell_trades)
    win_rate = round((len(wins) / total_closed) * 100, 1) if total_closed > 0 else 0

    # Average win/loss
    avg_win = round(np.mean([t['realized_pnl'] for t in wins]), 2) if wins else 0
    avg_loss = round(np.mean([t['realized_pnl'] for t in losses]), 2) if losses else 0

    # Profit factor
    gross_profit = sum(t['realized_pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['realized_pnl'] for t in losses)) if losses else 0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

    # Average hold time
    hold_times = [t['days_held'] for t in sell_trades if t['days_held'] is not None]
    avg_hold_days = round(np.mean(hold_times), 1) if hold_times else 0

    return {
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": total_return_pct,
        "total_realized_pnl": round(total_realized, 2),
        "total_commissions": round(total_commissions, 2),
        "net_profit": round(total_realized - total_commissions, 2),
        "total_trades": len(buy_trades),
        "closed_trades": total_closed,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "avg_hold_days": avg_hold_days,
    }


def _empty_metrics(initial_capital):
    """Return empty metrics structure when no data is available."""
    return {
        "initial_capital": initial_capital,
        "final_value": initial_capital,
        "total_return_pct": 0,
        "total_realized_pnl": 0,
        "total_commissions": 0,
        "net_profit": 0,
        "total_trades": 0,
        "closed_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0,
        "avg_win": 0,
        "avg_loss": 0,
        "profit_factor": 0,
        "max_drawdown_pct": 0,
        "avg_hold_days": 0,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("EMA Momentum Pullback Backtester")
    print("=" * 60)
    result = run_backtest(1000.0)
    metrics = result['metrics']
    trades = result['trades']
    print(f"\n{'-' * 40}")
    print(f"  Total Trades:    {metrics['total_trades']}")
    print(f"  Win Rate:        {metrics['win_rate']}%")
    print(f"  Profit Factor:   {metrics['profit_factor']}")
    print(f"  Total Return:    {metrics['total_return_pct']}%")
    print(f"  Max Drawdown:    {metrics['max_drawdown_pct']}%")
    print(f"  Avg Hold:        {metrics['avg_hold_days']} days")
    print(f"  Net Profit:      ${metrics['net_profit']}")
    print(f"  Final Value:     ${metrics['final_value']}")
    print(f"{'-' * 40}")

