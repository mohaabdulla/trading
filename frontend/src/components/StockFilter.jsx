import { useState, useEffect } from 'react'
import axios from 'axios'
import { Filter, TrendingUp, Activity, BarChart2, Shield, Target } from 'lucide-react'

const API_BASE = 'http://localhost:8000'

const StockFilter = ({ capital }) => {
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchScreenerData = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`${API_BASE}/api/screener?capital=${capital}`)
      setStocks(response.data.results)
      setLastUpdated(new Date().toLocaleTimeString())
    } catch (err) {
      console.error(err)
      setError("Failed to fetch screener data. Ensure the backend is running.")
      setStocks([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScreenerData()
  }, [capital])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

      {/* Header Panel */}
      <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={24} color="var(--accent-purple)" />
            EMA Momentum Pullback Scanner
          </h2>
          <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Scanning for: <strong>Price &gt; EMA 20 &gt; EMA 50</strong> • RSI 40-65 (pullback zone) • MACD histogram &gt; 0 • Volume &gt; 1.5× average
          </p>
          <p style={{ margin: '0.5rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            <Shield size={14} style={{ verticalAlign: 'middle', marginRight: '0.25rem' }} />
            Position sizing: 2% risk rule with ATR trailing stop (2×) • Capital: <strong>${capital.toLocaleString()}</strong>
          </p>
        </div>
        <button className="btn" onClick={fetchScreenerData} disabled={loading}>
          {loading ? 'Scanning...' : 'Run Scanner'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid var(--danger)', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      {/* Results Table */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>
            Matching Stocks ({stocks.length})
            {stocks.length > 0 && (
              <span style={{ fontSize: '0.8rem', fontWeight: 'normal', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                Sorted by RSI (best pullback first)
              </span>
            )}
          </h3>
          {lastUpdated && <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Last updated: {lastUpdated}</span>}
        </div>

        {loading && stocks.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
            <Activity size={48} className="animate-pulse" style={{ marginBottom: '1rem' }} />
            <p>Downloading data & calculating EMA, RSI, MACD, ATR indicators...</p>
            <p style={{ fontSize: '0.85rem' }}>This may take 10-15 seconds on first run.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '1rem 0.5rem' }}>Symbol</th>
                  <th style={{ padding: '1rem 0.5rem' }}>Price</th>
                  <th style={{ padding: '1rem 0.5rem' }}>RSI (14)</th>
                  <th style={{ padding: '1rem 0.5rem' }}>MACD Hist</th>
                  <th style={{ padding: '1rem 0.5rem' }}>ATR (14)</th>
                  <th style={{ padding: '1rem 0.5rem' }}>Volume</th>
                  <th style={{ padding: '1rem 0.5rem' }}>Stop Loss</th>
                  <th style={{ padding: '1rem 0.5rem' }}>Position Size</th>
                  <th style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>Risk</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map(stock => (
                  <tr key={stock.symbol} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s' }}>
                    <td style={{ padding: '1rem 0.5rem', fontWeight: 'bold', fontSize: '1.1rem' }}>{stock.symbol}</td>
                    <td style={{ padding: '1rem 0.5rem' }}>${stock.price.toFixed(2)}</td>
                    <td style={{ padding: '1rem 0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                          width: '40px', height: '6px', borderRadius: '3px',
                          background: 'rgba(255,255,255,0.1)', overflow: 'hidden', position: 'relative'
                        }}>
                          <div style={{
                            width: `${stock.rsi}%`, height: '100%', borderRadius: '3px',
                            background: stock.rsi <= 50 ? 'var(--success)' : stock.rsi <= 65 ? 'var(--accent-blue)' : 'var(--danger)',
                          }} />
                        </div>
                        <span style={{ color: stock.rsi <= 50 ? 'var(--success)' : stock.rsi <= 65 ? 'var(--accent-blue)' : 'var(--danger)' }}>
                          {stock.rsi}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: stock.macd > 0 ? 'var(--success)' : 'var(--danger)' }}>
                        <Activity size={16} />
                        {stock.macd}
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0.5rem' }}>
                      <span style={{ color: 'var(--accent-purple)' }}>${stock.atr}</span>
                    </td>
                    <td style={{ padding: '1rem 0.5rem' }}>
                      <div>
                        <span style={{ color: stock.volume_ratio >= 2 ? 'var(--success)' : 'var(--text-primary)' }}>
                          {(stock.volume / 1000000).toFixed(1)}M
                        </span>
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                        {stock.volume_ratio}× avg
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0.5rem' }}>
                      <div style={{ color: 'var(--danger)', fontWeight: 'bold' }}>
                        ${stock.stop_loss}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                        -${stock.risk_per_share}/share
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0.5rem' }}>
                      <div style={{ fontWeight: 'bold', color: 'var(--accent-blue)' }}>
                        {stock.suggested_shares} Shares
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                        ${stock.total_investment?.toFixed(2)}
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>
                      <div style={{ 
                        display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                        padding: '0.25rem 0.75rem', borderRadius: '4px',
                        background: 'rgba(239, 68, 68, 0.1)',
                        color: 'var(--danger)', fontWeight: 'bold', fontSize: '0.875rem'
                      }}>
                        <Target size={14} />
                        ${stock.risk_amount}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                        {((stock.risk_amount / capital) * 100).toFixed(1)}% of capital
                      </div>
                    </td>
                  </tr>
                ))}
                {stocks.length === 0 && !loading && (
                  <tr>
                    <td colSpan="9" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                      <div style={{ marginBottom: '0.5rem' }}>No stocks match the criteria right now.</div>
                      <div style={{ fontSize: '0.85rem' }}>
                        This is normal — the strategy waits for high-probability pullback setups. 
                        The market may be bearish (SPY &lt; 50 SMA) or no stocks are in the ideal RSI 40-65 zone with volume surge.
                      </div>
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

export default StockFilter
