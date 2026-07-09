import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const TILES = {
  dark:  { url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
           attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' },
  light: { url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
           attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' },
}

// Swaps tile layer reactively inside an existing MapContainer
function TileLayerSwitcher({ theme }) {
  const map = useMap()
  useEffect(() => { map.invalidateSize() }, [theme, map])
  const t = TILES[theme] ?? TILES.dark
  return <TileLayer key={theme} url={t.url} attribution={t.attribution} subdomains="abcd" maxZoom={20} />
}

// Fix Leaflet default icon paths broken by Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Custom drone icon (blue)
const droneIcon = L.divIcon({
  className: '',
  html: `<div style="
    width:14px;height:14px;
    background:#3b82f6;
    border:2px solid #fff;
    border-radius:50%;
    box-shadow:0 0 6px #3b82f6;
  "></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

// Custom node icon (orange)
const nodeIcon = L.divIcon({
  className: '',
  html: `<div style="
    width:10px;height:10px;
    background:#f97316;
    border:2px solid #fff;
    border-radius:50%;
    box-shadow:0 0 4px #f97316;
  "></div>`,
  iconSize: [10, 10],
  iconAnchor: [5, 5],
})

// Colour per drone route
const ROUTE_COLOURS = {
  'ROUTE-EAST-WEST':   '#3b82f6',
  'ROUTE-NORTH-SOUTH': '#10b981',
  'ROUTE-SOUTH-LOOP':  '#f59e0b',
}

// Keep last N positions per drone
const MAX_TRAIL = 80

function TrailPolyline({ trail, colour }) {
  if (trail.length < 2) return null
  return <Polyline positions={trail} color={colour} weight={2} opacity={0.7} />
}

function DroneLayer({ positions, onDroneClick }) {
  const [trails, setTrails] = useState({})

  useEffect(() => {
    const timer = setTimeout(() => {
      setTrails(prev => {
        const next = { ...prev }

        Object.entries(positions).forEach(([id, pos]) => {
          const existing = next[id] ? [...next[id]] : []
          const last = existing[existing.length - 1]
          if (!last || last[0] !== pos.lat || last[1] !== pos.lon) {
            existing.push([pos.lat, pos.lon])
            if (existing.length > MAX_TRAIL) existing.shift()
            next[id] = existing
          }
        })

        return next
      })
    }, 0)

    return () => clearTimeout(timer)
  }, [positions])

  return Object.entries(positions).map(([id, pos]) => {
    const colour = ROUTE_COLOURS[pos.route] ?? '#3b82f6'
    const trail = trails[id] ?? []
    return (
      <div key={id}>
        <TrailPolyline trail={trail} colour={colour} />
        <Marker position={[pos.lat, pos.lon]} icon={droneIcon}
          eventHandlers={{ click: () => onDroneClick?.(id) }}>
          <Popup>
            <strong>{id}</strong><br />
            Route: {pos.route}<br />
            Lat: {pos.lat?.toFixed(5)}<br />
            Lon: {pos.lon?.toFixed(5)}<br />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {pos.timestamp ? new Date(pos.timestamp * 1000).toLocaleTimeString() : ''}
            </span>
          </Popup>
        </Marker>
      </div>
    )
  })
}

export default function DroneMap({ positions, nodes, onDroneClick, theme = 'dark' }) {
  return (
    <MapContainer
      center={[22.5726, 88.3639]}
      zoom={12}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayerSwitcher theme={theme} />

      {/* Mesh nodes */}
      {nodes.map(node => (
        <Marker key={node.nodeId} position={[node.lat, node.lon]} icon={nodeIcon}>
          <Popup>
            <strong>{node.nodeId}</strong><br />
            {node.name}
          </Popup>
        </Marker>
      ))}

      {/* Live drones + trails */}
      <DroneLayer positions={positions} onDroneClick={onDroneClick} />
    </MapContainer>
  )
}
