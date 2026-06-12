import { useState, useEffect } from 'react'
import axios from 'axios'
import { Filter, TrendingUp, Activity, BarChart2 } from 'lucide-react'

const StockFilter = ({ capital }) => {
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchScreenerData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch live data from our backend, passing capital
      const response = await axios.get(`http://localhost:8000/api/screener?capital=${capital}`)
      setStocks(response.data.results)
      setLastUpdated(new Date().toLocaleTimeString())
    } catch (err) {
      console.error(err)
      setError("Failed to fetch screener data. Ensure the backend is running.")
      
      // Fallback mock data if backend isn't running
      setStocks([
        { symbol: "NVDA", price: 125.40, volume: 45000000, sma_50: 110.20, sma_200: 85.50, rsi: 68.5, suggested_shares: Math.floor(capital/125.4), total_investment: Math.floor(capital/125.4)*125.4 },
        { symbol: "META", price: 480.20, volume: 15000000, sma_50: 460.10, sma_200: 380.00, rsi: 62.1, suggested_shares: Math.floor(capital/480.2), total_investment: Math.floor(capital/480.2)*480.2 }
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScreenerData()
  }, [capital]) // Re-run when capital changes

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Header Panel */}
      <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={24} color="var(--accent-purple)" />
            High-Probability Setup Scanner
          </h2>
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
            Automatically filtering stocks for: Volume &gt; 2M, Price &gt; 50 SMA &gt; 200 SMA, RSI between 40-70.
          </p>
        </div>
        <button className="btn" onClick={fetchScreenerData} disabled={loading}>
          {loading ? 'Scanning...' : 'Run Scanner'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid var(--danger)', borderRadius: '4px' }}>
          {error} (Showing mock data for demonstration)
        </div>
      )}

      {/* Results Table */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Matching Stocks ({stocks.length})</h3>
          {lastUpdated && <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Last updated: {lastUpdated}</span>}
        </div>

        {loading && stocks.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
            <Activity size={48} className="animate-pulse" style={{ marginBottom: '1rem' }} />
            <p>Analyzing technical data...</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '1rem 0' }}>Symbol</th>
                  <th style={{ padding: '1rem 0' }}>Current Price</th>
                  <th style={{ padding: '1rem 0' }}>MACD (12,26,9)</th>
                  <th style={{ padding: '1rem 0' }}>SuperTrend (10,3)</th>
                  <th style={{ padding: '1rem 0' }}>Position Size</th>
                  <th style={{ padding: '1rem 0', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map(stock => (
                  <tr key={stock.symbol} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s' }}>
                    <td style={{ padding: '1rem 0', fontWeight: 'bold', fontSize: '1.1rem' }}>{stock.symbol}</td>
                    <td style={{ padding: '1rem 0' }}>${stock.price.toFixed(2)}</td>
                    <td style={{ padding: '1rem 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: stock.macd > 0 ? 'var(--success)' : 'var(--danger)' }}>
                        <Activity size={16} />
                        {stock.macd}
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: stock.supertrend === 'Bullish' ? 'var(--success)' : 'var(--danger)' }}>
                        <TrendingUp size={16} />
                        {stock.supertrend}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Trailing Stop Active
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0' }}>
                      <div style={{ fontWeight: 'bold', color: 'var(--accent-blue)' }}>
                        {stock.suggested_shares} Shares
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Inv: ${stock.total_investment?.toFixed(2)} | Vol: {(stock.volume / 1000000).toFixed(1)}M
                      </div>
                    </td>
                    <td style={{ padding: '1rem 0', textAlign: 'right' }}>
                      <button 
                        className="btn" 
                        style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                        onClick={() => alert(`Webhook Alert: Buy ${stock.suggested_shares} shares of ${stock.symbol}`)}
                      >
                        Trade Setup
                      </button>
                    </td>
                  </tr>
                ))}
                {stocks.length === 0 && !loading && (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                      No stocks match the strict criteria for the given capital.
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
