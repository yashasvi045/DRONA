import { useState, useEffect, useCallback } from 'react'

const API = 'http://localhost:8001'

const LABELS = {
  backend:    'API Backend',
  blockchain: 'Blockchain Node',
  mqtt:       'MQTT Broker',
  simulation: 'Simulation',
  websocket:  'WebSocket',
}

const ICONS = {
  backend:    '⬡',
  blockchain: '⛓',
  mqtt:       '⟳',
  simulation: '◈',
  websocket:  '⇄',
}

export default function SystemStatus({ onClose }) {
  const [health,  setHealth]  = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const fetchHealth = useCallback(() => {
    setLoading(true)
    setError(null)
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(setHealth)
      .catch(e => setError('Cannot reach backend - is it running?'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchHealth() }, [fetchHealth])

  // Close on backdrop click
  const onBackdrop = e => { if (e.target === e.currentTarget) onClose() }

  const subsystems = health
    ? Object.entries(LABELS).map(([key, label]) => ({
        key, label, icon: ICONS[key], ...(health[key] ?? {}),
      }))
    : []

  const allOk = subsystems.length > 0 && subsystems.every(s => s.ok)

  return (
    <div onClick={onBackdrop} style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 9999,
    }}>
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        width: 420,
        padding: '24px 28px',
        fontFamily: "'Rajdhani', 'Agency FB', sans-serif",
        color: 'var(--text-primary)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.3rem', letterSpacing: '0.1em', fontWeight: 700 }}>
              SYSTEM STATUS
            </h2>
            {health?.timestamp && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
                Last checked: {new Date(health.timestamp * 1000).toLocaleTimeString()}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={fetchHealth} disabled={loading} title="Refresh" style={{
              background: 'none', border: '1px solid var(--border)',
              color: 'var(--text-primary)', borderRadius: '50%',
              width: 28, height: 28, cursor: loading ? 'default' : 'pointer',
              fontSize: '0.95rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'inherit',
            }}>↻</button>
            <button onClick={onClose} title="Close" style={{
              background: 'none', border: '1px solid var(--border)',
              color: 'var(--text-primary)', borderRadius: '50%',
              width: 28, height: 28, cursor: 'pointer',
              fontSize: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'inherit',
            }}>✕</button>
          </div>
        </div>

        {/* Overall banner */}
        {health && (
          <div style={{
            padding: '8px 14px',
            borderRadius: 6,
            marginBottom: 18,
            background: allOk ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
            border: `1px solid ${allOk ? '#34d399' : '#f87171'}`,
            color: allOk ? '#34d399' : '#f87171',
            fontWeight: 600,
            fontSize: '0.85rem',
            letterSpacing: '0.06em',
          }}>
            {allOk ? '● ALL SYSTEMS NOMINAL' : '● DEGRADED - CHECK BELOW'}
          </div>
        )}

        {/* Loading / error */}
        {loading && (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center' }}>
            Checking subsystems…
          </p>
        )}
        {error && (
          <p style={{ color: '#f87171', fontSize: '0.85rem' }}>{error}</p>
        )}

        {/* Subsystem rows */}
        {!loading && subsystems.map(s => (
          <div key={s.key} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '10px 0',
            borderBottom: '1px solid var(--border-subtle)',
          }}>
            <span style={{ fontSize: '1.1rem', width: 22, textAlign: 'center', color: 'var(--text-muted)' }}>
              {s.icon}
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: '0.88rem', letterSpacing: '0.05em' }}>
                {s.label}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 1 }}>
                {s.detail ?? '-'}
              </div>
            </div>
            <span style={{
              fontSize: '0.7rem', fontWeight: 700,
              padding: '3px 9px', borderRadius: 4,
              letterSpacing: '0.08em',
              background: s.ok ? 'rgba(52,211,153,0.15)' : 'rgba(248,113,113,0.15)',
              color:      s.ok ? '#34d399'                : '#f87171',
              border:     `1px solid ${s.ok ? '#34d399' : '#f87171'}`,
            }}>
              {s.ok ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
