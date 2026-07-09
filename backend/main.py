"""
main.py - Drone Mesh Tracker Backend
--------------------------------------
Endpoints:
  GET  /nodes               → list of all Kolkata mesh nodes
  GET  /drones              → on-chain registered drones
  GET  /drones/{id}         → single drone on-chain record
  GET  /drones/{id}/logs    → on-chain passage history
  GET  /positions           → current live positions (in-memory store)
  WS   /ws                  → real-time drone telemetry stream

Run:
  uvicorn backend.main:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .chain_client import get_all_drones, get_drone, get_passage_logs
from .mqtt_client import start_mqtt
from .store import store
from .ws_manager import manager

# Import Kolkata nodes so the REST endpoint can serve them
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "simulation"))
from nodes import NODES  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Startup / Shutdown ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop  = asyncio.get_running_loop()
    queue = asyncio.Queue()

    # Start MQTT subscriber in background thread
    mqtt_client = start_mqtt(loop, queue)
    app.state.mqtt_client = mqtt_client

    # Background coroutine: drain the queue and broadcast to WebSocket clients
    async def broadcaster():
        while True:
            payload = await queue.get()
            await manager.broadcast({"type": "telemetry", "data": payload})

    task = asyncio.create_task(broadcaster())
    app.state.broadcaster_task = task

    log.info("Backend started - listening for drone telemetry")
    yield

    # Shutdown
    task.cancel()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    log.info("Backend shut down cleanly")


app = FastAPI(title="Drone Mesh Tracker API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.get("/nodes")
def list_nodes():
    """Return all Kolkata mesh nodes."""
    return [
        {"nodeId": nid, **data}
        for nid, data in NODES.items()
    ]


@app.get("/drones")
async def list_drones():
    """Return all registered drones from the smart contract."""
    drones = await asyncio.to_thread(get_all_drones)
    return drones


@app.get("/drones/{drone_id}")
async def get_drone_info(drone_id: str):
    """Return a single drone's on-chain record."""
    drone = await asyncio.to_thread(get_drone, drone_id)
    if drone is None:
        raise HTTPException(status_code=404, detail="Drone not found")
    return drone


@app.get("/drones/{drone_id}/logs")
async def drone_logs(drone_id: str):
    """Return on-chain passage logs for a drone."""
    logs = await asyncio.to_thread(get_passage_logs, drone_id)
    return logs


@app.get("/positions")
def live_positions():
    """Return the latest telemetry position for every drone seen this session."""
    return store.all()


@app.get("/health")
async def health():
    """System operational health - checks all subsystems."""
    import time
    from web3 import Web3

    result = {}

    # 1. Backend itself
    result["backend"] = {"ok": True, "detail": "API server running"}

    # 2. Blockchain / smart contract
    try:
        drones = await asyncio.to_thread(get_all_drones)
        result["blockchain"] = {
            "ok": True,
            "detail": f"Connected · {len(drones)} drone(s) registered",
        }
    except Exception as e:
        result["blockchain"] = {"ok": False, "detail": str(e)}

    # 3. MQTT - inferred from whether store has been updated recently
    positions = store.all()
    if positions:
        freshest = max(p.get("timestamp", 0) for p in positions.values())
        age = int(time.time()) - int(freshest)
        mqtt_ok = age < 10
        result["mqtt"] = {
            "ok": mqtt_ok,
            "detail": f"Last telemetry {age}s ago" if mqtt_ok else f"No telemetry for {age}s",
        }
    else:
        result["mqtt"] = {"ok": False, "detail": "No telemetry received yet"}

    # 4. Simulation - active if any positions in store
    result["simulation"] = {
        "ok": bool(positions),
        "detail": f"{len(positions)} drone(s) transmitting" if positions else "No active drones",
    }

    # 5. WebSocket clients
    client_count = len(manager._clients)
    result["websocket"] = {
        "ok": True,
        "detail": f"{client_count} client(s) connected",
    }

    result["timestamp"] = int(time.time())
    return result


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send current snapshot immediately on connect
    await ws.send_json({"type": "snapshot", "data": store.all()})
    try:
        while True:
            await ws.receive_text()   # keep connection alive; client can send pings
    except WebSocketDisconnect:
        manager.disconnect(ws)
