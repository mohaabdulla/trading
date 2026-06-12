import yfinance as yf
from backtester import TICKERS, processed_data
import pandas as pd
import datetime

def test_strat():
    from backtester import processed_data, sorted_dates
    
    cash = 100.0
    open_positions = []
    trade_history = []
    
    for current_date in sorted_dates:
        positions_to_close = []
        for pos in open_positions:
            ticker = pos['symbol']
            if ticker in processed_data and current_date in processed_data[ticker].index:
                row = processed_data[ticker].loc[current_date]
                current_price = float(row['Close'])
                supertrend_dir = float(row['SUPERTd_10_3'])
                
                # Check if we have RSI
                if 'RSI_14' not in row:
                    from pandas_ta import rsi
                    processed_data[ticker]['RSI_14'] = rsi(processed_data[ticker]['Close'], length=14)
                    row = processed_data[ticker].loc[current_date]
                
                rsi_val = float(row['RSI_14']) if 'RSI_14' in row else 50
                macd_line = float(row['MACD_12_26_9'])
                macd_signal = float(row['MACDs_12_26_9'])
                
                # Exit: Fast MACD cross down OR Overbought RSI OR Supertrend bearish
                if macd_line < macd_signal or rsi_val > 70 or supertrend_dir != 1:
                    sell_value = pos['quantity'] * current_price
                    realized_pnl = sell_value - pos['cost_basis']
                    cash += sell_value
                    cash -= 1.00
                    trade_history.append({'pnl': realized_pnl, 'comm': 1.0})
                    positions_to_close.append(pos)
                    
        for pos in positions_to_close:
            open_positions.remove(pos)
            
        if cash >= 2.0 and len(open_positions) == 0:
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
                    
                    if 'RSI_14' not in row:
                        from pandas_ta import rsi
                        processed_data[ticker]['RSI_14'] = rsi(processed_data[ticker]['Close'], length=14)
                        row = processed_data[ticker].loc[current_date]
                    rsi_val = float(row['RSI_14']) if 'RSI_14' in row else 50
                    
                    if current_price < 2 or avg_vol < 2000000: continue
                    if supertrend_dir != 1: continue
                    if macd_line <= macd_signal: continue
                    
                    # Buy the dip: RSI should be relatively low (not overbought)
                    if rsi_val > 60: continue
                    
                    buy_candidates.append({
                        "symbol": ticker,
                        "price": current_price,
                        "macd": macd_hist
                    })
            
            # Sort by least overbought (lowest RSI) instead of highest MACD
            # Actually we don't have rsi in dict, let's just sort by MACD for now
            buy_candidates.sort(key=lambda x: x['macd'], reverse=True)
            
            for best_setup in buy_candidates:
                price = best_setup['price']
                quantity = int(cash // price)
                if quantity > 0:
                    cost_basis = quantity * price
                    cash -= cost_basis
                    cash -= 1.00
                    open_positions.append({
                        "symbol": best_setup['symbol'],
                        "quantity": quantity,
                        "cost_basis": cost_basis
                    })
                    break

    realized = sum(t['pnl'] for t in trade_history)
    comm = sum(t['comm'] for t in trade_history) * 2 # round trip approx
    print(f"Trades: {len(trade_history)}")
    print(f"Realized PnL: ${realized:.2f}")
    print(f"Commissions: ${comm:.2f}")
    print(f"Net Profit: ${realized - comm:.2f}")

if __name__ == "__main__":
    import backtester
    backtester.run_backtest(100.0) # To populate processed_data
    test_strat()
