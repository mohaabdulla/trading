import { useState, useEffect } from 'react'
import axios from 'axios'
import { History, TrendingUp, TrendingDown, DollarSign, Clock, Play, Award, Target, BarChart3, Timer, ArrowDownRight } from 'lucide-react'

const API_BASE = 'http://localhost:8000'

const TradingHistory = ({ capital }) => {
  const [trades, setTrades] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [isBacktest, setIsBacktest] = useState(false)

  const fetchLiveHistory = async () => {
    setLoading(true)
    setIsBacktest(false)
    setMetrics(null)
    try {
      const response = await axios.get(`${API_BASE}/api/trades`)
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
      const response = await axios.get(`${API_BASE}/api/backtest?capital=${capital}`)
      const data = response.data
      // New format: { trades: [...], metrics: {...} }
      if (data.trades) {
        setTrades(data.trades)
        setMetrics(data.metrics)
      } else {
        // Fallback for old format (flat array)
        setTrades(Array.isArray(data) ? data : [])
        setMetrics(null)
      }
    } catch (err) {
      console.error("Failed to run backtest", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLiveHistory()
  }, [])

  // Calculate totals from trade data
  const totalRealizedGain = trades.reduce((sum, t) => sum + (t.realized_pnl || 0), 0)
  const totalCommissions = trades.reduce((sum, t) => sum + (t.commission || 0), 0)
  const netProfit = totalRealizedGain - totalCommissions

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

      {/* Performance Metrics Cards (shown after backtest) */}
      {metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
          
          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              <span>Total Return</span>
              <TrendingUp size={16} color={metrics.total_return_pct >= 0 ? "var(--success)" : "var(--danger)"} />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: metrics.total_return_pct >= 0 ? 'var(--success)' : 'var(--danger)' }}>
              {metrics.total_return_pct >= 0 ? '+' : ''}{metrics.total_return_pct}%
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              ${metrics.initial_capital} → ${metrics.final_value}
            </div>
          </div>

          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              <span>Win Rate</span>
              <Award size={16} color="var(--accent-blue)" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: metrics.win_rate >= 50 ? 'var(--success)' : 'var(--danger)' }}>
              {metrics.win_rate}%
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {metrics.wins}W / {metrics.losses}L of {metrics.closed_trades} closed
            </div>
          </div>

          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              <span>Profit Factor</span>
              <Target size={16} color="var(--accent-purple)" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: metrics.profit_factor >= 1 ? 'var(--success)' : 'var(--danger)' }}>
              {metrics.profit_factor === Infinity ? '∞' : metrics.profit_factor}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Avg Win: ${metrics.avg_win} | Avg Loss: ${metrics.avg_loss}
            </div>
          </div>

          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              <span>Max Drawdown</span>
              <ArrowDownRight size={16} color="var(--danger)" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: 'var(--danger)' }}>
              -{metrics.max_drawdown_pct}%
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Largest peak-to-trough decline
            </div>
          </div>

          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              <span>Avg Hold Time</span>
              <Timer size={16} color="var(--accent-blue)" />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 'bold' }}>
              {metrics.avg_hold_days}d
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {metrics.total_trades} total trades
            </div>
          </div>

          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              <span>Net Profit</span>
              <DollarSign size={16} color={metrics.net_profit >= 0 ? "var(--success)" : "var(--danger)"} />
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: metrics.net_profit >= 0 ? 'var(--success)' : 'var(--danger)' }}>
              ${metrics.net_profit}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Commissions: -${metrics.total_commissions}
            </div>
          </div>

        </div>
      )}

      {/* Simple summary when no backtest metrics */}
      {!metrics && (
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
      )}

      {/* Trade History Table */}
      <div className="glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: '0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <History size={24} color="var(--accent-blue)" />
            {isBacktest ? `Backtest Results (2020–Today, $${capital})` : "Live Trade History"}
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
            <div style={{ marginBottom: '1rem' }}>
              <BarChart3 size={48} style={{ animation: 'pulse 1.5s ease-in-out infinite' }} />
            </div>
            {isBacktest 
              ? "Simulating thousands of trading days with EMA Momentum Pullback strategy... This takes about 15 seconds." 
              : "Loading..."}
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
                  {isBacktest && <th style={{ padding: '1rem 0' }}>Exit Reason</th>}
                  <th style={{ padding: '1rem 0', textAlign: 'right' }}>Realized Gain/Loss</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade, i) => (
                  <tr key={trade.id || i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
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
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>@ ${trade.price?.toFixed(2)}</div>
                    </td>
                    <td style={{ padding: '1rem 0', color: 'var(--danger)' }}>
                      ${trade.commission ? trade.commission.toFixed(2) : '0.00'}
                    </td>
                    {isBacktest && (
                      <td style={{ padding: '1rem 0' }}>
                        {trade.exit_reason && (
                          <span style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 'bold',
                            background: trade.exit_reason === 'RSI_OB' ? 'rgba(139, 92, 246, 0.2)' :
                                         trade.exit_reason === 'STOP' ? 'rgba(239, 68, 68, 0.2)' :
                                         'rgba(59, 130, 246, 0.2)',
                            color: trade.exit_reason === 'RSI_OB' ? 'var(--accent-purple)' :
                                   trade.exit_reason === 'STOP' ? 'var(--danger)' :
                                   'var(--accent-blue)',
                          }}>
                            {trade.exit_reason === 'STOP' ? '🛑 Stop Hit' :
                             trade.exit_reason === 'RSI_OB' ? '📈 RSI Overbought' :
                             trade.exit_reason === 'TIME' ? '⏰ Time Stop' : trade.exit_reason}
                          </span>
                        )}
                        {trade.days_held != null && trade.action === 'SELL' && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                            Held {trade.days_held}d
                          </div>
                        )}
                      </td>
                    )}
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
                    <td colSpan={isBacktest ? "7" : "6"} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                      {isBacktest 
                        ? "No trades generated. Try adjusting the capital amount."
                        : "No trades have been executed yet. Click 'Run Backtest' to simulate the strategy."}
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
