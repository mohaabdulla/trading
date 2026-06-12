import { useState, useEffect } from 'react'
import axios from 'axios'
import { Activity, DollarSign, PieChart, ArrowUpRight, ArrowDownRight } from 'lucide-react'

const Dashboard = () => {
  const [summary, setSummary] = useState(null)
  const [positions, setPositions] = useState([])
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // In a real app, these endpoints would point to your FastAPI backend
        // e.g. http://localhost:8000/api/summary
        // For now we will just mock the data to show the premium UI
        
        // Mock data to simulate API response
        setTimeout(() => {
          setSummary({
            net_liquidation: 105432.50,
            total_cash: 25000.00,
            unrealized_pnl: 4500.75,
            realized_pnl: 1250.25,
            total_commission: 45.50
          })
          
          setPositions([
            { symbol: 'AAPL', position: 100, avgCost: 150.50, currentPrice: 175.20 },
            { symbol: 'TSLA', position: -50, avgCost: 200.00, currentPrice: 180.50 },
            { symbol: 'MSFT', position: 200, avgCost: 310.00, currentPrice: 330.10 }
          ])
          
          setTrades([
            { id: 1, symbol: 'AAPL', action: 'BUY', quantity: 100, price: 150.50, commission: 1.00, timestamp: '2023-10-27T14:30:00Z' },
            { id: 2, symbol: 'TSLA', action: 'SELL', quantity: 50, price: 200.00, commission: 0.50, timestamp: '2023-10-26T10:15:00Z' }
          ])
          
          setLoading(false)
        }, 1000)
      } catch (err) {
        setError('Failed to fetch data')
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <div className="text-gradient" style={{ fontSize: '1.5rem', fontWeight: 'bold', animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}>
          Loading Portfolio Data...
        </div>
      </div>
    )
  }

  if (error) return <div style={{ color: 'var(--danger)' }}>{error}</div>

  return (
    <div style={{ display: 'grid', gap: '2rem' }}>
      {/* Top Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
        
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
            <span>Net Liquidation</span>
            <DollarSign size={20} color="var(--accent-blue)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
            ${summary?.net_liquidation.toLocaleString(undefined, {minimumFractionDigits: 2})}
          </div>
        </div>

        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
            <span>Unrealized PnL</span>
            <Activity size={20} color={summary?.unrealized_pnl >= 0 ? "var(--success)" : "var(--danger)"} />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: summary?.unrealized_pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
            {summary?.unrealized_pnl >= 0 ? '+' : '-'}${Math.abs(summary?.unrealized_pnl || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
          </div>
        </div>

        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)' }}>
            <span>Total Commissions Paid</span>
            <PieChart size={20} color="var(--accent-purple)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-secondary)' }}>
            ${summary?.total_commission.toLocaleString(undefined, {minimumFractionDigits: 2})}
          </div>
        </div>

      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
        {/* Active Positions */}
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
                    <td style={{ padding: '1rem 0' }}>${pos.avgCost.toFixed(2)}</td>
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

        {/* Recent Trades Activity */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Recent Trades</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {trades.map(trade => (
              <div key={trade.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontWeight: 'bold' }}>{trade.symbol}</span>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {new Date(trade.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                  <span style={{ color: trade.action === 'BUY' ? 'var(--success)' : 'var(--danger)', fontWeight: 'bold' }}>
                    {trade.action} {trade.quantity}
                  </span>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Fee: ${trade.commission.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
