import { useState, useEffect } from 'react'
import axios from 'axios'
import { History, TrendingUp, TrendingDown, DollarSign, Clock, Play } from 'lucide-react'

const TradingHistory = ({ capital }) => {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(false)
  const [isBacktest, setIsBacktest] = useState(false)

  const fetchLiveHistory = async () => {
    setLoading(true)
    setIsBacktest(false)
    try {
      const response = await axios.get('http://localhost:8000/api/trades')
      setTrades(response.data)
    } catch (err) {
      console.error("Failed to fetch live history", err)
      setTrades([])
    } finally {
      setLoading(false)
    }
  }

  const runBacktest = async () => {
    setLoading(true)
    setIsBacktest(true)
    try {
      const response = await axios.get(`http://localhost:8000/api/backtest?capital=${capital}`)
      setTrades(response.data)
    } catch (err) {
      console.error("Failed to run backtest", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLiveHistory()
  }, [])

  // Calculate totals
  const totalRealizedGain = trades.reduce((sum, t) => sum + (t.realized_pnl || 0), 0)
  const totalCommissions = trades.reduce((sum, t) => sum + (t.commission || 0), 0)
  const netProfit = totalRealizedGain - totalCommissions

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="glass-panel" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-secondary)' }}>Total Realized Gain/Loss</h3>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: totalRealizedGain >= 0 ? 'var(--success)' : 'var(--danger)', display: 'flex', alignItems: 'center' }}>
            <DollarSign size={28} />
            {totalRealizedGain.toFixed(2)}
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-secondary)' }}>Total IBKR Commissions</h3>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--danger)', display: 'flex', alignItems: 'center' }}>
            -<DollarSign size={28} />
            {totalCommissions.toFixed(2)}
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-secondary)' }}>Net Profit</h3>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: netProfit >= 0 ? 'var(--success)' : 'var(--danger)', display: 'flex', alignItems: 'center' }}>
            <DollarSign size={28} />
            {netProfit.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: '0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <History size={24} color="var(--accent-blue)" />
            {isBacktest ? "Backtest Results (2020-Today)" : "Live Trade History"}
          </h2>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button className="btn" onClick={fetchLiveHistory} disabled={loading} style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', boxShadow: 'none' }}>
              View Live History
            </button>
            <button className="btn" onClick={runBacktest} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Play size={16} />
              {loading && isBacktest ? "Running Simulation..." : "Run Backtest"}
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
            {isBacktest ? "Simulating thousands of historical days... This takes about 10 seconds." : "Loading..."}
          </div>
        ) : (
          <div style={{ overflowX: 'auto', maxHeight: '600px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-card)', zIndex: 1 }}>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '1rem 0' }}>Date</th>
                  <th style={{ padding: '1rem 0' }}>Symbol</th>
                  <th style={{ padding: '1rem 0' }}>Action</th>
                  <th style={{ padding: '1rem 0' }}>Quantity & Price</th>
                  <th style={{ padding: '1rem 0' }}>Commission</th>
                  <th style={{ padding: '1rem 0', textAlign: 'right' }}>Realized Gain/Loss</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '1rem 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                        <Clock size={16} />
                        {new Date(trade.timestamp).toLocaleDateString()}
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0', fontWeight: 'bold', fontSize: '1.1rem' }}>{trade.symbol}</td>
                    <td style={{ padding: '1rem 0' }}>
                      <span style={{ 
                        padding: '0.25rem 0.75rem', 
                        borderRadius: '4px',
                        fontSize: '0.875rem',
                        fontWeight: 'bold',
                        background: trade.action.includes('BUY') ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: trade.action.includes('BUY') ? 'var(--success)' : 'var(--danger)'
                      }}>
                        {trade.action}
                      </span>
                    </td>
                    <td style={{ padding: '1rem 0' }}>
                      <div>{trade.quantity} shares</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>@ ${trade.price.toFixed(2)}</div>
                    </td>
                    <td style={{ padding: '1rem 0', color: 'var(--danger)' }}>
                      ${trade.commission ? trade.commission.toFixed(2) : '0.00'}
                    </td>
                    <td style={{ padding: '1rem 0', textAlign: 'right', fontWeight: 'bold', fontSize: '1.1rem' }}>
                      {trade.realized_pnl !== null && trade.realized_pnl !== undefined ? (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem', color: trade.realized_pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                          {trade.realized_pnl >= 0 ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
                          ${Math.abs(trade.realized_pnl).toFixed(2)}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 'normal' }}>Open Position</span>
                      )}
                    </td>
                  </tr>
                ))}
                {trades.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                      No trades have been executed yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default TradingHistory
