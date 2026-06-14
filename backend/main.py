from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import database
from ibkr_client import ibkr
import uvicorn
import asyncio
from contextlib import asynccontextmanager

# Pydantic models for request validation
class WebhookPayload(BaseModel):
    passphrase: str
    symbol: str
    action: str # 'BUY' or 'SELL'
    quantity: float

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to connect to IBKR on startup
    connected = await ibkr.connect_async()
    if connected:
        print("Connected to IBKR Gateway/TWS.")
    else:
        print("WARNING: Could not connect to IBKR. Check if Gateway/TWS is running on port 4002.")
    yield
    # Disconnect on shutdown
    ibkr.disconnect()

app = FastAPI(lifespan=lifespan)

# Allow CORS for the frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secret passphrase to secure webhooks from TradingView
WEBHOOK_PASSPHRASE = "super_secret_trading_passphrase"

@app.get("/")
def read_root():
    return {
        "message": "TradingBot Pro backend is running.",
        "strategy": "EMA Momentum Pullback",
        "docs": "/docs",
        "status": "online",
        "ibkr_connected": ibkr.connected
    }

@app.post("/webhook")
async def tradingview_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    """
    Endpoint for TradingView webhooks to trigger trades.
    """
    if payload.passphrase != WEBHOOK_PASSPHRASE:
        raise HTTPException(status_code=403, detail="Invalid passphrase")
    
    # Place order via IBKR
    result = ibkr.place_order(payload.symbol, payload.action, payload.quantity)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    # Log trade to database
    db_trade = database.Trade(
        symbol=payload.symbol,
        action=payload.action,
        quantity=payload.quantity,
        status="SUBMITTED" # Ideally we'd listen for execution events to update this
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    
    return {"message": "Trade executed", "trade": db_trade}

@app.get("/api/summary")
def get_account_summary():
    if not ibkr.connected:
        return {"error": "IBKR not connected", "status": "offline"}
    return {"summary": ibkr.get_account_summary(), "status": "online"}

@app.get("/api/positions")
def get_positions():
    if not ibkr.connected:
        return {"error": "IBKR not connected"}
    return ibkr.get_positions()

@app.get("/api/trades")
def get_trades(db: Session = Depends(get_db)):
    trades = db.query(database.Trade).order_by(database.Trade.timestamp.desc()).limit(50).all()
    return trades

@app.get("/api/screener")
def get_screener_results(capital: float = 1000.0):
    import screener
    results = screener.run_screener(capital)
    return {"results": results}

@app.get("/api/backtest")
def run_backtest_endpoint(capital: float = 1000.0, use_time_stop: bool = True,
                          zero_commission: bool = False):
    import backtester
    # This might take 10-15 seconds as it downloads 4+ years of data
    result = backtester.run_backtest(
        initial_capital=capital,
        start_date="2020-01-01",
        use_time_stop=use_time_stop,
        zero_commission=zero_commission,
    )
    return result  # Returns {"trades": [...], "metrics": {...}}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "ibkr_connected": ibkr.connected,
        "strategy": "EMA Momentum Pullback",
        "risk_per_trade": "Adaptive (2-5%)",
        "max_positions": "1-3 (by capital)",
        "stop_type": "ATR Trailing Stop (2x) + Breakeven (Momentum-Aware)",
        "commission": "IBKR Tiered ($0.35 min)",
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
