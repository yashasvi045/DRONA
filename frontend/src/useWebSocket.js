import { useEffect, useRef, useState, useCallback } from 'react'

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

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      // auto-reconnect after 2s
      setTimeout(connect, 2000)
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
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return { positions, connected }
}
