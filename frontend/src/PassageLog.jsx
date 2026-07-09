import { useState, useEffect, useCallback } from 'react'

const API = 'http://localhost:8001'

export default function PassageLog({ selectedDrone }) {
  const [logs,    setLogs]    = useState([])
  const [loading, setLoading] = useState(false)
  const [tick,    setTick]    = useState(0)   // increment to trigger refresh

  const fetchLogs = useCallback(() => {
    if (!selectedDrone) { setLogs([]); return }
    setLoading(true)
    fetch(`${API}/drones/${selectedDrone}/logs`)
      .then(r => r.json())
      .then(data => setLogs(data.reverse()))
      .catch(() => setLogs([]))
      .finally(() => setLoading(false))
  }, [selectedDrone, tick]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const timer = setTimeout(fetchLogs, 0)
    return () => clearTimeout(timer)
  }, [fetchLogs])

  if (!selectedDrone) {
    return <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Click a drone marker to see its passage log</p>
  }

  return (
    <>
      {/* Header row with refresh button */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginBottom: 6 }}>
        <button
          onClick={() => setTick(t => t + 1)}
          disabled={loading}
          title="Refresh passage log"
          style={{
            background: 'none',
            border: '1px solid var(--border)',
            color: loading ? 'var(--text-muted)' : 'var(--text-primary)',
            borderRadius: '50%',
            width: 26, height: 26,
            cursor: loading ? 'default' : 'pointer',
            fontSize: '0.9rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'transform 0.3s',
            transform: loading ? 'rotate(360deg)' : 'none',
            fontFamily: 'inherit',
          }}
        >↻</button>
      </div>

      {loading && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading…</p>}

      {!loading && !logs.length && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No passages logged yet for {selectedDrone}</p>
      )}

      {!loading && logs.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {logs.map((log, i) => (
            <li key={i} style={{
              padding: '7px 0',
              borderBottom: '1px solid var(--border-subtle)',
              fontSize: '0.8rem',
            }}>
              <div style={{ fontWeight: 600, color: 'var(--accent-orange)' }}>{log.nodeId}</div>
              <div style={{ color: 'var(--text-primary)' }}>
                {log.lat?.toFixed(5)}, {log.lon?.toFixed(5)}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                {log.timestamp
                  ? new Date(log.timestamp * 1000).toLocaleString()
                  : '-'}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
