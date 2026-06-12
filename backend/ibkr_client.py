from ib_insync import *
import asyncio

# Patch asyncio to allow nested event loops, which is often needed 
# when mixing ib_insync with other async frameworks like FastAPI.
import nest_asyncio
nest_asyncio.apply()

class IBKRClient:
    def __init__(self, host='127.0.0.1', port=4002, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self.account_summary = {}
        self.positions = []

    async def connect_async(self):
        try:
            # We use connectAsync because FastAPI already has a running event loop
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            self.connected = True
            
            # Request updates
            self.ib.reqAccountSummary()
            self.ib.accountSummaryEvent += self._on_account_summary
            self.ib.positionEvent += self._on_position
            
            return True
        except Exception as e:
            print(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()
        self.connected = False

    def _on_account_summary(self, value):
        self.account_summary[value.tag] = value.value

    def _on_position(self, position):
        # Update positions list
        self.positions = self.ib.positions()

    def place_order(self, symbol, action, quantity):
        if not self.connected:
            return {"error": "Not connected to IBKR"}
        
        contract = Stock(symbol, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)
        
        order = MarketOrder(action, quantity)
        trade = self.ib.placeOrder(contract, order)
        
        return {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_id": order.orderId
        }

    def get_account_summary(self):
        return self.account_summary

    def get_positions(self):
        return [{"symbol": p.contract.symbol, "position": p.position, "avgCost": p.avgCost} for p in self.positions]

ibkr = IBKRClient()
