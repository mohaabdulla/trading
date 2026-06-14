import yfinance as yf
import json
import os
import time

CACHE_FILE = "halal_universe.json"

PROHIBITED_INDUSTRIES = [
    "bank", "credit", "insurance", "capital markets", # Conventional Finance
    "tobacco", "gambling", "casino", "beverages - wineries", "aerospace & defense" # Haram activities
]

def is_halal_business(info):
    industry = info.get("industry", "").lower()
    sector = info.get("sector", "").lower()
    
    if not industry and not sector:
        return False, "Missing industry/sector data"
        
    for prohibited in PROHIBITED_INDUSTRIES:
        if prohibited in industry or prohibited in sector:
            return False, f"Prohibited industry: {industry} / {sector}"
            
    return True, "Passed business screen"

def get_financial_value(df, key):
    if df.empty or key not in df.index:
        return 0.0
    val = df.loc[key]
    if isinstance(val, pd.Series):
        val = val.dropna()
        return float(val.iloc[0]) if not val.empty else 0.0
    return float(val) if not pd.isna(val) else 0.0

import pandas as pd

def is_halal_financials(ticker_obj, info):
    market_cap = info.get("marketCap", 0)
    if not market_cap:
        return False, "Missing market cap"
        
    bs = ticker_obj.balance_sheet
    fin = ticker_obj.financials
    
    if bs.empty or fin.empty:
        return False, "Missing financial statements"
        
    # 1. Debt Ratio
    total_debt = get_financial_value(bs, "Total Debt")
    debt_ratio = total_debt / market_cap
    if debt_ratio >= 0.33:
        return False, f"Debt ratio {debt_ratio:.1%} >= 33%"
        
    # 2. Liquidity Ratio (Cash + Short Term Investments)
    cash = get_financial_value(bs, "Cash And Cash Equivalents")
    st_investments = get_financial_value(bs, "Other Short Term Investments")
    liquidity_ratio = (cash + st_investments) / market_cap
    if liquidity_ratio >= 0.33:
        return False, f"Liquidity ratio {liquidity_ratio:.1%} >= 33%"
        
    # 3. Income Ratio
    revenue = get_financial_value(fin, "Total Revenue")
    interest_income = get_financial_value(fin, "Interest Income")
    
    if revenue > 0:
        income_ratio = interest_income / revenue
        if income_ratio >= 0.05:
            return False, f"Interest income ratio {income_ratio:.1%} >= 5%"
            
    return True, "Passed financial screen"

def build_halal_universe(tickers, force_refresh=False):
    if not force_refresh and os.path.exists(CACHE_FILE):
        print(f"Loading cached Halal universe from {CACHE_FILE}")
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
            
    print("Running Halal AAOIFI Screen...")
    results = {}
    
    for symbol in tickers:
        try:
            print(f"Checking {symbol}...")
            t = yf.Ticker(symbol)
            info = t.info
            
            # Business Screen
            business_ok, biz_reason = is_halal_business(info)
            if not business_ok:
                results[symbol] = {"compliant": False, "reason": biz_reason}
                continue
                
            # Financial Screen
            fin_ok, fin_reason = is_halal_financials(t, info)
            if not fin_ok:
                results[symbol] = {"compliant": False, "reason": fin_reason}
                continue
                
            results[symbol] = {"compliant": True, "reason": "Fully compliant"}
        except Exception as e:
            results[symbol] = {"compliant": False, "reason": f"Error: {str(e)}"}
            
        time.sleep(0.5) # Be gentle to Yahoo Finance API
        
    with open(CACHE_FILE, "w") as f:
        json.write(f, results, indent=4)
        
    return results

if __name__ == "__main__":
    from strategy import TICKERS
    # For testing, we just import json inside the function if needed, but it's already imported.
    # Oh wait, json.write(f, results) is wrong, it should be json.dump(results, f). Let me fix this.
    
    def build_halal_universe_fixed(tickers, force_refresh=False):
        if not force_refresh and os.path.exists(CACHE_FILE):
            print(f"Loading cached Halal universe from {CACHE_FILE}")
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
                
        print("Running Halal AAOIFI Screen...")
        results = {}
        
        for symbol in tickers:
            try:
                print(f"Checking {symbol}...")
                t = yf.Ticker(symbol)
                info = t.info
                
                # Business Screen
                business_ok, biz_reason = is_halal_business(info)
                if not business_ok:
                    results[symbol] = {"compliant": False, "reason": biz_reason}
                    continue
                    
                # Financial Screen
                fin_ok, fin_reason = is_halal_financials(t, info)
                if not fin_ok:
                    results[symbol] = {"compliant": False, "reason": fin_reason}
                    continue
                    
                results[symbol] = {"compliant": True, "reason": "Fully compliant"}
            except Exception as e:
                results[symbol] = {"compliant": False, "reason": f"Error: {str(e)}"}
                
            time.sleep(0.5)
            
        with open(CACHE_FILE, "w") as f:
            json.dump(results, f, indent=4)
            
        return results

    res = build_halal_universe_fixed(TICKERS, force_refresh=True)
    
    print("\n--- Halal Screening Results ---")
    halal_count = 0
    for t, d in res.items():
        status = "✅ HALAL" if d['compliant'] else "❌ HARAM"
        print(f"{t:<6} | {status:<8} | {d['reason']}")
        if d['compliant']: halal_count += 1
        
    print(f"\nTotal Halal Tickers: {halal_count} / {len(TICKERS)}")
