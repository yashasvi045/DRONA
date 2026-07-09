export default function DroneStatus({ drones, positions, selected, onSelect }) {
  if (!drones.length) {
    return <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No drones registered</p>
  }

  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {drones.map(drone => {
        const live = positions[drone.droneId]
        return (
          <li key={drone.droneId} onClick={() => onSelect?.(drone.droneId)} style={{
            cursor: 'pointer',
            outline: selected === drone.droneId ? '1px solid #3b82f6' : 'none',
            borderRadius: 4,
            padding: '8px 0',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            {/* Status dot */}
            <span style={{
              width: 9, height: 9,
              borderRadius: '50%',
              background: drone.isActive ? '#34d399' : '#f87171',
              flexShrink: 0,
            }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{drone.droneId}</div>
              {live ? (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)' }}>
                  {live.lat?.toFixed(5)}, {live.lon?.toFixed(5)}
                  <span style={{ marginLeft: 6, color: 'var(--text-secondary)' }}>
                    {live.route}
                  </span>
                </div>
              ) : (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>no signal</div>
              )}
            </div>
            <span style={{
              fontSize: '0.7rem',
              padding: '2px 6px',
              borderRadius: 4,
              background: drone.isActive ? '#064e3b' : '#4c0519',
              color:      drone.isActive ? '#86efac' : '#fca5a5',
            }}>
              {drone.isActive ? 'ACTIVE' : 'GROUNDED'}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
