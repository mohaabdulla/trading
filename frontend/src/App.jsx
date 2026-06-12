import { useState } from 'react'
import Dashboard from './components/Dashboard'
import StockFilter from './components/StockFilter'
import TradingHistory from './components/TradingHistory'
import './index.css'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [capital, setCapital] = useState(1000)

  return (
    <div style={{ padding: '2rem', width: '100%', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 className="text-gradient" style={{ margin: 0, fontSize: '2.5rem' }}>TradingBot Pro</h1>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-card)', padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <label style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Available Capital: $</label>
            <input 
              type="number" 
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', fontSize: '1rem', width: '80px', outline: 'none', fontWeight: 'bold' }}
            />
          </div>

          <nav style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              className={`btn ${activeTab === 'dashboard' ? '' : 'inactive'}`} 
              onClick={() => setActiveTab('dashboard')}
              style={activeTab !== 'dashboard' ? { background: 'var(--bg-secondary)', color: 'var(--text-secondary)', boxShadow: 'none' } : {}}
            >
              Dashboard
            </button>
            <button 
              className={`btn ${activeTab === 'filter' ? '' : 'inactive'}`} 
              onClick={() => setActiveTab('filter')}
              style={activeTab !== 'filter' ? { background: 'var(--bg-secondary)', color: 'var(--text-secondary)', boxShadow: 'none' } : {}}
            >
              Stock Filter
            </button>
            <button 
              className={`btn ${activeTab === 'history' ? '' : 'inactive'}`} 
              onClick={() => setActiveTab('history')}
              style={activeTab !== 'history' ? { background: 'var(--bg-secondary)', color: 'var(--text-secondary)', boxShadow: 'none' } : {}}
            >
              Trading History
            </button>
          </nav>
        </div>
      </header>

      <main className="animate-fade-in">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'filter' && <StockFilter capital={capital} />}
        {activeTab === 'history' && <TradingHistory capital={capital} />}
      </main>
    </div>
  )
}

export default App
