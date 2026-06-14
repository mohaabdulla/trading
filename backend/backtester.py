import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from strategy import (
    TICKERS, ATR_STOP_MULTIPLIER, ATR_TARGET_MULTIPLIER, RISK_PCT, MIN_TRADE_VALUE, 
    MAX_HOLD_DAYS, RSI_OVERBOUGHT, MAX_COMMISSION_DRAG, MAX_EXPOSURE_PCT,
    COMMISSION_PER_SHARE, MIN_COMMISSION,
    calculate_indicators, is_buy_signal
)


def calc_commission(shares: int, zero_commission: bool = False) -> float:
    """Commission model. Set zero_commission=True to simulate Webull/Robinhood."""
    if zero_commission:
        return 0.0
    return round(max(MIN_COMMISSION, shares * COMMISSION_PER_SHARE), 2)


def run_backtest(initial_capital: float = 100.0, start_date="2020-01-01",
                 use_time_stop=True, zero_commission=False):
    """
    Run a full backtest of the EMA Momentum Pullback strategy.
    
    Args:
        initial_capital: Starting cash amount
        start_date: Backtest start date
        use_time_stop: If True, enforce MAX_HOLD_DAYS exit
        zero_commission: If True, simulate zero-commission broker (Webull/Robinhood)
    """
    broker_label = "Zero-Commission" if zero_commission else "IBKR"
    time_label = f"Time Stop: {use_time_stop}"
    print(f"\nStarting backtest with ${initial_capital} ({broker_label}, {time_label}) from {start_date}...")

    # Download SPY
    print("Downloading SPY market data...")
    try:
        spy_df = yf.download("SPY", start=start_date, progress=False)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)
        spy_df['SMA_50'] = spy_df['Close'].rolling(window=50).mean()
    except Exception as e:
        spy_df = pd.DataFrame()

    # Download Tickers
    print("Downloading historical data...")
    try:
        data = yf.download(TICKERS, start=start_date, group_by='ticker', progress=False)
    except Exception as e:
        return {"trades": [], "metrics": _empty_metrics(initial_capital)}

    # Pre-calculate indicators
    processed_data = {}
    all_dates = set()
    print("Calculating technical indicators...")
    for ticker in TICKERS:
        try:
            if len(TICKERS) == 1:
                df = data.copy()
            else:
                df = data[ticker].copy()
            
            df = calculate_indicators(df)
            if not df.empty:
                processed_data[ticker] = df
                all_dates.update(df.index)
        except Exception:
            continue

    if not all_dates:
        return {"trades": [], "metrics": _empty_metrics(initial_capital)}

    sorted_dates = sorted(list(all_dates))
    
    # State
    cash = initial_capital
    unsettled_cash = 0.0
    open_positions = []
    trade_history = []
    equity_curve = []
    
    # Look-ahead queue: signals generated on Day T, executed Day T+1 Open
    pending_buy_orders = [] 

    print(f"Simulating {len(sorted_dates)} trading days...")

    for i, current_date in enumerate(sorted_dates):
        # 1. Settle cash from yesterday (T+1 Settlement)
        cash += unsettled_cash
        unsettled_cash = 0.0

        # Track equity before today's moves
        portfolio_value = cash
        for pos in open_positions:
            ticker = pos['symbol']
            if ticker in processed_data and current_date in processed_data[ticker].index:
                portfolio_value += pos['quantity'] * float(processed_data[ticker].loc[current_date]['Close'])
            else:
                portfolio_value += pos['quantity'] * pos['entry_price']
        equity_curve.append(portfolio_value)

        # 2. Execute Pending Buy Orders (at OPEN, Day T+1)
        for order in pending_buy_orders:
            ticker = order['symbol']
            if ticker not in processed_data or current_date not in processed_data[ticker].index:
                continue
                
            row = processed_data[ticker].loc[current_date]
            open_price = float(row['Open'])
            
            # Recalculate based on real open price to avoid over-allocation
            quantity = order['shares']
            cost_basis = quantity * open_price
            buy_commission = calc_commission(quantity, zero_commission)
            
            if cost_basis + buy_commission > cash:
                available_for_trade = cash - buy_commission
                if available_for_trade > 0:
                    quantity = int(available_for_trade // open_price)
                    cost_basis = quantity * open_price
                    buy_commission = calc_commission(quantity, zero_commission)
                else:
                    quantity = 0
            
            if quantity > 0 and (cost_basis + buy_commission <= cash):
                cash -= cost_basis
                cash -= buy_commission
                
                initial_stop = open_price - order['stop_distance']
                
                trade_history.append({
                    "symbol": ticker,
                    "action": "BUY",
                    "quantity": quantity,
                    "price": round(open_price, 2),
                    "timestamp": current_date.isoformat() + "Z",
                    "realized_pnl": None,
                    "commission": buy_commission,
                    "exit_reason": None,
                    "days_held": None,
                })

                open_positions.append({
                    "symbol": ticker,
                    "quantity": quantity,
                    "entry_price": open_price,
                    "cost_basis": cost_basis,
                    "trailing_stop": initial_stop,
                    "entry_date": current_date,
                    "days_held": 0,
                    "atr_at_entry": order['atr'],
                    "breakeven_active": False,
                })
                
        pending_buy_orders = []

        # 3. Check Exits (End of Day T)
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

            # Breakeven stop: MACD <= 0 and in profit by 1x ATR
            if not pos.get('breakeven_active') and current_price >= pos['entry_price'] + pos['atr_at_entry'] and macd_hist <= 0:
                pos['breakeven_active'] = True
                if pos['entry_price'] > pos['trailing_stop']:
                    pos['trailing_stop'] = pos['entry_price']

            # Update trailing stop (moves UP with high price, never down)
            new_stop = high_price - (ATR_STOP_MULTIPLIER * atr_val)
            if new_stop > pos['trailing_stop']:
                pos['trailing_stop'] = new_stop

            # EXIT CONDITIONS
            exit_reason = None
            sell_price = current_price
            
            target_price = pos['entry_price'] + (pos['atr_at_entry'] * ATR_TARGET_MULTIPLIER)

            if high_price >= target_price:
                exit_reason = "TARGET"
                sell_price = target_price
            elif current_price <= pos['trailing_stop']:
                exit_reason = "STOP"
                sell_price = current_price
            elif rsi_val > RSI_OVERBOUGHT:
                exit_reason = "RSI_OB"
                sell_price = current_price
            elif use_time_stop and pos['days_held'] >= MAX_HOLD_DAYS:
                exit_reason = "TIME"
                sell_price = current_price

            if exit_reason:
                sell_value = pos['quantity'] * sell_price
                realized_pnl = sell_value - pos['cost_basis']
                sell_commission = calc_commission(pos['quantity'], zero_commission)
                
                # T+1 Settlement: funds go to unsettled_cash, NOT cash
                unsettled_cash += sell_value
                cash -= sell_commission  # Commissions are paid immediately

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

        # 4. Check Entries (End of Day T) - Signals added to pending_buy_orders
        market_ok = True
        if not spy_df.empty and current_date in spy_df.index:
            spy_row = spy_df.loc[current_date]
            if float(spy_row['Close']) <= float(spy_row['SMA_50']):
                market_ok = False

        if market_ok:
            held_symbols = {pos['symbol'] for pos in open_positions}
            
            # Use portfolio equity to calculate risk (fixed fractional)
            current_equity = cash + unsettled_cash + sum(p['quantity'] * p['entry_price'] for p in open_positions)
            dollar_risk = current_equity * RISK_PCT
            
            max_total_exposure = current_equity * MAX_EXPOSURE_PCT
            current_exposure = sum(p['quantity'] * p['entry_price'] for p in open_positions)
            remaining_exposure = max_total_exposure - current_exposure
            
            buy_candidates = []

            for ticker, df in processed_data.items():
                if ticker in held_symbols: continue
                if current_date not in df.index: continue

                row = df.loc[current_date]
                if is_buy_signal(row):
                    atr_val = float(row['ATRr_14'])
                    close_price = float(row['Close'])
                    
                    stop_distance = atr_val * ATR_STOP_MULTIPLIER
                    suggested_shares = int(dollar_risk / stop_distance)
                    
                    if suggested_shares > 0:
                        buy_candidates.append({
                            "symbol": ticker,
                            "close": close_price,
                            "rsi": float(row['RSI_14']),
                            "atr": atr_val,
                            "shares": suggested_shares,
                            "stop_distance": stop_distance,
                        })

            # Sort by RSI ascending (buy the deepest pullback)
            buy_candidates.sort(key=lambda x: x['rsi'])

            projected_cash = cash + unsettled_cash
            
            for candidate in buy_candidates:
                cost_basis = candidate['shares'] * candidate['close']
                buy_comm = calc_commission(candidate['shares'], zero_commission)
                
                if cost_basis + buy_comm > projected_cash: continue 
                if cost_basis > remaining_exposure: continue
                if cost_basis < MIN_TRADE_VALUE: continue
                if not zero_commission and buy_comm > 0 and (buy_comm * 2) / cost_basis > MAX_COMMISSION_DRAG: continue
                    
                pending_buy_orders.append(candidate)
                projected_cash -= (cost_basis + buy_comm)
                remaining_exposure -= cost_basis


    # Mark remaining open positions
    for pos in open_positions:
        trade_history.append({
            "symbol": pos['symbol'],
            "action": "BUY (OPEN)",
            "quantity": pos['quantity'],
            "price": round(pos['entry_price'], 2),
            "timestamp": pos['entry_date'].isoformat() + "Z",
            "realized_pnl": None,
            "commission": calc_commission(pos['quantity'], zero_commission),
            "exit_reason": None,
            "days_held": pos['days_held'],
        })

    metrics = _calculate_metrics(trade_history, equity_curve, initial_capital, cash + unsettled_cash, open_positions)
    trade_history.sort(key=lambda x: x['timestamp'], reverse=True)
    for i, t in enumerate(trade_history): t['id'] = i + 1

    return {"trades": trade_history, "metrics": metrics}


def _calculate_metrics(trade_history, equity_curve, initial_capital, final_cash, open_positions):
    sell_trades = [t for t in trade_history if t['action'] == 'SELL']
    buy_trades = [t for t in trade_history if t['action'] == 'BUY']

    wins = [t for t in sell_trades if t['realized_pnl'] and t['realized_pnl'] > 0]
    losses = [t for t in sell_trades if t['realized_pnl'] and t['realized_pnl'] <= 0]

    total_realized = sum(t['realized_pnl'] for t in sell_trades if t['realized_pnl'])
    total_commissions = sum(t['commission'] for t in trade_history if t['commission'])

    final_value = final_cash
    for pos in open_positions:
        final_value += pos['quantity'] * pos['entry_price']

    total_return_pct = round(((final_value - initial_capital) / initial_capital) * 100, 2) if initial_capital > 0 else 0

    max_drawdown_pct = 0
    if equity_curve:
        peak = equity_curve[0]
        for val in equity_curve:
            if val > peak: peak = val
            drawdown = ((peak - val) / peak) * 100 if peak > 0 else 0
            if drawdown > max_drawdown_pct: max_drawdown_pct = drawdown

    total_closed = len(sell_trades)
    win_rate = round((len(wins) / total_closed) * 100, 1) if total_closed > 0 else 0

    avg_win = round(np.mean([t['realized_pnl'] for t in wins]), 2) if wins else 0
    avg_loss = round(np.mean([t['realized_pnl'] for t in losses]), 2) if losses else 0

    gross_profit = sum(t['realized_pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['realized_pnl'] for t in losses)) if losses else 0
    
    commission_drag_pct = round((total_commissions / gross_profit) * 100, 2) if gross_profit > 0 else 100.0

    net_profit = total_realized - total_commissions
    expectancy = round(net_profit / total_closed, 2) if total_closed > 0 else 0.0
    
    # Profit factor: gross_profit / (gross_loss + commissions)
    total_costs = gross_loss + total_commissions
    profit_factor = round(gross_profit / total_costs, 2) if total_costs > 0 else 0

    hold_times = [t['days_held'] for t in sell_trades if t['days_held'] is not None]
    avg_hold_days = round(np.mean(hold_times), 1) if hold_times else 0

    return {
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": total_return_pct,
        "total_realized_pnl": round(total_realized, 2),
        "total_commissions": round(total_commissions, 2),
        "net_profit": round(net_profit, 2),
        "total_trades": len(buy_trades),
        "closed_trades": total_closed,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "commission_drag_pct": commission_drag_pct,
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "avg_hold_days": avg_hold_days,
    }

def _empty_metrics(initial_capital):
    return {
        "initial_capital": initial_capital, "final_value": initial_capital, "total_return_pct": 0,
        "total_realized_pnl": 0, "total_commissions": 0, "net_profit": 0, "total_trades": 0,
        "closed_trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "avg_win": 0, "avg_loss": 0,
        "profit_factor": 0, "expectancy": 0, "commission_drag_pct": 0, "max_drawdown_pct": 0, "avg_hold_days": 0,
    }

if __name__ == "__main__":
    print("=" * 80)
    print("EMA Momentum Pullback Backtester — 4-Way Comparison")
    print("=" * 80)
    
    scenarios = [
        {"label": "IBKR + Time Stop",       "use_time_stop": True,  "zero_commission": False},
        {"label": "IBKR + No Time Stop",     "use_time_stop": False, "zero_commission": False},
        {"label": "Zero-Comm + Time Stop",   "use_time_stop": True,  "zero_commission": True},
        {"label": "Zero-Comm + No Time Stop","use_time_stop": False, "zero_commission": True},
    ]
    
    results = {}
    for s in scenarios:
        res = run_backtest(1000.0, start_date="2020-01-01", 
                          use_time_stop=s["use_time_stop"], 
                          zero_commission=s["zero_commission"])
        results[s["label"]] = res['metrics']
    
    print("\n" + "=" * 115)
    print("BACKTEST RESULTS — Starting Capital: $1000.00")
    print("=" * 115)
    
    headers = list(results.keys())
    print(f"{'Metric':<25}", end="")
    for h in headers:
        print(f" | {h:<20}", end="")
    print()
    print("-" * 115)
    
    rows = [
        ("Total Trades",    "total_trades",    "{}"),
        ("Win Rate",         "win_rate",        "{}%"),
        ("Avg Win",          "avg_win",         "${}"),
        ("Avg Loss",         "avg_loss",        "${}"),
        ("Expectancy",       "expectancy",      "${}"),
        ("Profit Factor",    "profit_factor",   "{}"),
        ("Net Profit",       "net_profit",      "${}"),
        ("Final Value",      "final_value",     "${}"),
        ("Max Drawdown",     "max_drawdown_pct","{}%"),
        ("Commissions",      "total_commissions","${}"),
        ("Commission Drag",  "commission_drag_pct","{}%"),
        ("Avg Hold Days",    "avg_hold_days",   "{}"),
    ]
    
    for label, key, fmt in rows:
        print(f"{label:<25}", end="")
        for h in headers:
            val = results[h].get(key, 0)
            print(f" | {fmt.format(val):<20}", end="")
        print()
    
    print("-" * 115)
    
    # Warnings
    for h in headers:
        m = results[h]
        if m['expectancy'] <= 0:
            print(f"\n[WARNING] {h}: NEGATIVE expectancy (${m['expectancy']}/trade). No edge.")
        if m['commission_drag_pct'] > 50:
            print(f"[WARNING] {h}: Commissions consuming {m['commission_drag_pct']}% of gross profits.")
