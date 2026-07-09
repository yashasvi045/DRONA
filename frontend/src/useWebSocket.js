import { useEffect, useRef, useState } from 'react'

const WS_URL = 'ws://localhost:8001/ws'

/**
 * useWebSocket - connects to the backend WebSocket and returns live state.
 *
 * Returns:
 *   positions  - { [droneId]: { lat, lon, route, timestamp } }
 *   connected  - boolean
 */
export function useWebSocket() {
  const [positions, setPositions] = useState({})
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    let disposed = false
    let reconnectTimer = null

    const connect = () => {
      if (disposed) return

      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!disposed) {
          // auto-reconnect after 2s
          reconnectTimer = setTimeout(connect, 2000)
        }
      }
      ws.onerror = () => ws.close()

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'snapshot') {
            setPositions(msg.data)
          } else if (msg.type === 'telemetry') {
            const d = msg.data
            setPositions(prev => ({ ...prev, [d.drone_id]: d }))
          }
        } catch {
          // ignore malformed messages
        }
      }
    }

    connect()

    return () => {
      disposed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      wsRef.current?.close()
    }
  }, [])

  return { positions, connected }
}
