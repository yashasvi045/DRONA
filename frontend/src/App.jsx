import { useState, useEffect } from 'react'
import './App.css'
import { useWebSocket } from './useWebSocket'
import DroneMap      from './DroneMap'
import DroneStatus   from './DroneStatus'
import PassageLog    from './PassageLog'
import SystemStatus  from './SystemStatus'

const API = 'http://localhost:8001'

function App() {
  const [nodes,         setNodes]         = useState([])
  const [drones,        setDrones]        = useState([])
  const [selectedDrone, setSelectedDrone] = useState(null)
  const [theme,         setTheme]         = useState('dark')
  const [showStatus,    setShowStatus]    = useState(false)
  const { positions, connected }          = useWebSocket()

  useEffect(() => {
    fetch(`${API}/nodes`).then(r => r.json()).then(setNodes).catch(() => {})
    fetch(`${API}/drones`).then(r => r.json()).then(setDrones).catch(() => {})
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  return (
    <div className="app-shell">
      {/* ── Header ── */}
      <header className="app-header">
        <span className="app-title">DRONA</span>
        <div className="header-right">
          <button className="theme-toggle" onClick={() => setShowStatus(true)}>
            ◈ STATUS
          </button>
          <span className={`conn-badge ${connected ? 'conn-live' : 'conn-off'}`}>
            {connected ? '● Live' : '○ Connecting…'}
          </span>
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'dark' ? '☀ Light' : '☾ Dark'}
          </button>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="app-body">
        {/* Left Sidebar */}
        <aside className="sidebar">
          <section className="panel">
            <h2 className="panel-title">Drones</h2>
            <DroneStatus
              drones={drones}
              positions={positions}
              selected={selectedDrone}
              onSelect={setSelectedDrone}
            />
          </section>

          <section className="panel">
            <h2 className="panel-title">
              Passage Log
              {selectedDrone && (
                <span style={{ color: 'var(--accent-blue)', fontWeight: 400 }}> - {selectedDrone}</span>
              )}
            </h2>
            <PassageLog selectedDrone={selectedDrone} />
          </section>
        </aside>

        {/* Map */}
        <main className="map-area">
          <DroneMap
            positions={positions}
            nodes={nodes}
            onDroneClick={setSelectedDrone}
            theme={theme}
          />
        </main>
      </div>

      {showStatus && <SystemStatus onClose={() => setShowStatus(false)} />}
    </div>
  )
}

export default App
