# TradingBot Pro

This project contains a trading bot backend that connects to Interactive Brokers (IBKR) via TWS/Gateway, and a premium React frontend dashboard.

## Prerequisites
1. **Interactive Brokers TWS or IB Gateway** installed and running.
   - Go to Settings -> API -> Settings.
   - Check "Enable ActiveX and Socket Clients".
   - Set Socket port to `4002` (for paper trading) or `7497`. (Update `ibkr_client.py` if using a different port).
2. **Python 3.9+**
3. **Node.js**

## Running the Backend
1. Open a terminal and navigate to `backend/`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Running the Frontend Dashboard
1. Open a terminal and navigate to `frontend/`.
2. Start the Vite dev server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:5173` in your browser.

## Connecting to TradingView
1. In TradingView, set up your Pine Script alerts.
2. Set the Webhook URL to your backend's public IP or domain: `http://YOUR_IP:8000/webhook` (You may need ngrok for local testing).
3. Set the message payload to JSON format:
   ```json
   {
     "passphrase": "super_secret_trading_passphrase",
     "symbol": "{{ticker}}",
     "action": "BUY",
     "quantity": 100
   }
   ```
