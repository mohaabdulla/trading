import yfinance as yf

def test_ticker(symbol):
    try:
        t = yf.Ticker(symbol)
        info = t.info
        print(f"--- {symbol} ---")
        print(f"Sector: {info.get('sector')}")
        print(f"Industry: {info.get('industry')}")
        
        bs = t.balance_sheet
        fin = t.financials
        
        print("Balance Sheet available:", not bs.empty)
        if not bs.empty:
            print("Total Debt:", bs.loc['Total Debt'].iloc[0] if 'Total Debt' in bs.index else 'N/A')
            print("Cash:", bs.loc['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in bs.index else 'N/A')
            
        print("Financials available:", not fin.empty)
        if not fin.empty:
            print("Total Revenue:", fin.loc['Total Revenue'].iloc[0] if 'Total Revenue' in fin.index else 'N/A')
            print("Interest Income:", fin.loc['Interest Income'].iloc[0] if 'Interest Income' in fin.index else 'N/A')
            
    except Exception as e:
        print(f"Error on {symbol}: {e}")

test_ticker("AAPL")
test_ticker("SOFI")
test_ticker("RIOT")
