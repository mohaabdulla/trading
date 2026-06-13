import { useState, useEffect } from 'react'
import axios from 'axios'
import { Activity, DollarSign, PieChart, ArrowUpRight, ArrowDownRight, Wifi, WifiOff, Shield, TrendingUp, Zap } from 'lucide-react'

const API_BASE = 'http://localhost:8000'

const Dashboard = () => {
  const [summary, setSummary] = useState(null)
  const [positions, setPositions] = useState([])
  const [trades, setTrades] = useState([])
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch system status
        const statusRes = await axios.get(`${API_BASE}/api/status`).catch(() => null)
        if (statusRes?.data) {
          setStatus(statusRes.data)
        }

        // Fetch account summary from IBKR
        const summaryRes = await axios.get(`${API_BASE}/api/summary`).catch(() => null)
        if (summaryRes?.data && !summaryRes.data.error) {
          setSummary(summaryRes.data.summary)
        }

        // Fetch positions
        const posRes = await axios.get(`${API_BASE}/api/positions`).catch(() => null)
        if (posRes?.data && !posRes.data.error && Array.isArray(posRes.data)) {
          setPositions(posRes.data)
        }

        // Fetch recent trades from DB
        const tradesRes = await axios.get(`${API_BASE}/api/trades`).catch(() => null)
        if (tradesRes?.data && Array.isArray(tradesRes.data)) {
          setTrades(tradesRes.data)
        }

        setLoading(false)
      } catch (err) {
        setError('Failed to connect to backend')
        setLoading(false)
      }
    }

    fetchData()
    // Poll every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  const ibkrConnected = status?.ibkr_connected || false

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <div className="text-gradient" style={{ fontSize: '1.5rem', fontWeight: 'bold', animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}>
          Connecting to Backend...
        </div>
      </div>
    )
  }

  if (error) return <div style={{ color: 'var(--danger)' }}>{error}</div>

  return (
    <div style={{ display: 'grid', gap: '2rem' }}>

      {/* Strategy Info & Connection Status */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        
        {/* Connection Status */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
            <span>IBKR Connection</span>
            {ibkrConnected ? <Wifi size={20} color="var(--success)" /> : <WifiOff size={20} color="var(--danger)" />}
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: ibkrConnected ? 'var(--success)' : 'var(--danger)' }}>
            {ibkrConnected ? 'Connected' : 'Offline'}
          </div>
          {!ibkrConnected && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              TWS/Gateway not running on port 4002. Backtest mode available.
            </div>
          )}
        </div>

        {/* Strategy Card */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
            <span>Active Strategy</span>
            <Zap size={20} color="var(--accent-purple)" />
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
            {status?.strategy || 'EMA Momentum Pullback'}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            EMA 20/50 • RSI 40-65 • MACD • ATR Stop
          </div>
        </div>

        {/* Risk Management Card */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
            <span>Risk Management</span>
            <Shield size={20} color="var(--accent-blue)" />
          </div>
          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-blue)' }}>
                {status?.risk_per_trade || '2%'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Risk/Trade</div>
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-purple)' }}>
                {status?.max_positions || 3}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Max Positions</div>
            </div>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {status?.stop_type || 'ATR Trailing Stop (2x)'}
          </div>
        </div>
      </div>

      {/* Account Summary (show when IBKR connected) */}
      {ibkrConnected && summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
              <span>Net Liquidation</span>
              <DollarSign size={20} color="var(--accent-blue)" />
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
              ${parseFloat(summary?.NetLiquidation || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
            </div>
          </div>

          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
              <span>Unrealized PnL</span>
              <Activity size={20} color={parseFloat(summary?.UnrealizedPnL || 0) >= 0 ? "var(--success)" : "var(--danger)"} />
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: parseFloat(summary?.UnrealizedPnL || 0) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
              {parseFloat(summary?.UnrealizedPnL || 0) >= 0 ? '+' : ''}${parseFloat(summary?.UnrealizedPnL || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
            </div>
          </div>

          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
              <span>Available Cash</span>
              <PieChart size={20} color="var(--accent-purple)" />
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
              ${parseFloat(summary?.TotalCashValue || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
            </div>
          </div>
        </div>
      )}

      {/* When IBKR offline, show helpful info */}
      {!ibkrConnected && (
        <div className="glass-panel" style={{ 
          background: 'rgba(59, 130, 246, 0.05)', 
          border: '1px solid rgba(59, 130, 246, 0.2)',
          display: 'flex', 
          flexDirection: 'column', 
          gap: '1rem' 
        }}>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-blue)' }}>
            <TrendingUp size={20} />
            Backtest Mode Active
          </h3>
          <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            IBKR Gateway/TWS is not connected. You can still use the <strong>Stock Filter</strong> to find live screener results 
            and <strong>Trading History</strong> to run backtests with historical data. 
            To enable live trading, start TWS or IB Gateway on port 4002 and restart the backend.
          </p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: positions.length > 0 ? '2fr 1fr' : '1fr', gap: '2rem' }}>
        {/* Active Positions */}
        {positions.length > 0 && (
          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Active Positions</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th style={{ paddingBottom: '0.75rem' }}>Symbol</th>
                  <th style={{ paddingBottom: '0.75rem' }}>Qty</th>
                  <th style={{ paddingBottom: '0.75rem' }}>Avg Cost</th>
                  <th style={{ paddingBottom: '0.75rem' }}>Unrealized PnL</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(pos => {
                  const pnl = (pos.currentPrice - pos.avgCost) * pos.position
                  return (
                    <tr key={pos.symbol} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '1rem 0', fontWeight: 'bold' }}>{pos.symbol}</td>
                      <td style={{ padding: '1rem 0', color: pos.position > 0 ? 'var(--success)' : 'var(--danger)' }}>{pos.position}</td>
                      <td style={{ padding: '1rem 0' }}>${pos.avgCost?.toFixed(2)}</td>
                      <td style={{ padding: '1rem 0', color: pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          {pnl >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                          ${Math.abs(pnl).toFixed(2)}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Recent Trades Activity */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <h3 style={{ margin: 0, fontSize: '1.25rem' }}>
            {trades.length > 0 ? 'Recent Live Trades' : 'Trade Activity'}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {trades.length > 0 ? trades.slice(0, 5).map((trade, i) => (
              <div key={trade.id || i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontWeight: 'bold' }}>{trade.symbol}</span>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {trade.timestamp ? new Date(trade.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                  <span style={{ color: trade.action?.includes('BUY') ? 'var(--success)' : 'var(--danger)', fontWeight: 'bold' }}>
                    {trade.action} {trade.quantity}
                  </span>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    @ ${trade.price?.toFixed(2) || '—'}
                  </span>
                </div>
              </div>
            )) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <Activity size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                <p style={{ margin: 0 }}>No live trades yet. Run a backtest or connect IBKR to get started.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
