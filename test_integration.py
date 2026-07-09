"""
DRONA - End-to-End Integration Test Suite (Step 5)
====================================================
Tests the full pipeline:
  Hardhat node  →  SmartContract  →  MQTT broker
       →  FastAPI backend (REST + WebSocket)  →  On-chain passage logs

Run:
  .venv\\Scripts\\python.exe test_integration.py
"""

import sys, time, json, threading, asyncio
import requests
import websocket          # websocket-client (already pulled in by web3 deps)
import paho.mqtt.client as mqtt
from web3 import Web3

# ─── Config ───────────────────────────────────────────────────────────────────
BACKEND   = "http://localhost:8001"
WS_URL    = "ws://localhost:8001/ws"
RPC_URL   = "http://127.0.0.1:8545"
MQTT_HOST = "localhost"
MQTT_PORT = 1883
CONTRACT  = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

PASS = "\033[92m✔\033[0m"
FAIL = "\033[91m✘\033[0m"
INFO = "\033[94m·\033[0m"

results = []

def check(label, ok, detail=""):
    mark = PASS if ok else FAIL
    print(f"  {mark}  {label}" + (f"  ({detail})" if detail else ""))
    results.append((label, ok))


# ─── 1. Hardhat / Web3 ────────────────────────────────────────────────────────
print("\n[1] Blockchain node")
try:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    connected = w3.is_connected()
    check("Web3 connected to Hardhat (8545)", connected)
    if connected:
        block = w3.eth.block_number
        check("Chain is producing blocks", block >= 0, f"block #{block}")
        code = w3.eth.get_code(Web3.to_checksum_address(CONTRACT))
        check("DroneRegistry contract deployed", len(code) > 2, f"{len(code)} bytes")
except Exception as e:
    check("Web3 connection", False, str(e))


# ─── 2. MQTT broker ───────────────────────────────────────────────────────────
print("\n[2] MQTT broker")
mqtt_connected = threading.Event()
mqtt_msg_received = threading.Event()
mqtt_payload = {}

def _on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        mqtt_connected.set()
        client.subscribe("drone/+/telemetry")

def _on_message(client, userdata, msg):
    try:
        mqtt_payload.update(json.loads(msg.payload))
        mqtt_msg_received.set()
    except Exception:
        pass

mc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mc.on_connect = _on_connect
mc.on_message = _on_message
try:
    mc.connect(MQTT_HOST, MQTT_PORT, keepalive=5)
    mc.loop_start()
    ok = mqtt_connected.wait(timeout=4)
    check("MQTT broker reachable (1883)", ok)
    if ok:
        got_msg = mqtt_msg_received.wait(timeout=6)
        check("Receiving live drone telemetry via MQTT", got_msg,
              f"drone_id={mqtt_payload.get('drone_id','?')}" if got_msg else "no message - is simulator running?")
    mc.loop_stop()
    mc.disconnect()
except Exception as e:
    check("MQTT connection", False, str(e))


# ─── 3. FastAPI REST endpoints ────────────────────────────────────────────────
print("\n[3] FastAPI backend REST (8001)")
try:
    r = requests.get(f"{BACKEND}/nodes", timeout=4)
    nodes = r.json()
    check("GET /nodes returns data", r.status_code == 200 and len(nodes) > 0,
          f"{len(nodes)} nodes")
except Exception as e:
    check("GET /nodes", False, str(e))
    nodes = []

try:
    r = requests.get(f"{BACKEND}/drones", timeout=4)
    drones = r.json()
    check("GET /drones returns data", r.status_code == 200 and len(drones) > 0,
          f"{len(drones)} drones")
except Exception as e:
    check("GET /drones", False, str(e))
    drones = []

try:
    r = requests.get(f"{BACKEND}/positions", timeout=4)
    positions = r.json()
    check("GET /positions returns live data", r.status_code == 200 and len(positions) > 0,
          f"{len(positions)} active drones - is simulator running?" if len(positions) == 0 else f"{len(positions)} drones tracked")
except Exception as e:
    check("GET /positions", False, str(e))
    positions = {}

if drones:
    drone_id = drones[0]["droneId"]
    try:
        r = requests.get(f"{BACKEND}/drones/{drone_id}", timeout=4)
        check(f"GET /drones/{{id}} returns drone info", r.status_code == 200,
              f"droneId={r.json().get('droneId','?')}")
    except Exception as e:
        check("GET /drones/{id}", False, str(e))

    try:
        r = requests.get(f"{BACKEND}/drones/{drone_id}/logs", timeout=4)
        logs = r.json()
        check(f"GET /drones/{{id}}/logs returns passage logs", r.status_code == 200,
              f"{len(logs)} passage(s) on-chain" if logs else "0 passages - simulator may not have crossed a node yet")
    except Exception as e:
        check("GET /drones/{id}/logs", False, str(e))


# ─── 4. WebSocket live stream ─────────────────────────────────────────────────
print("\n[4] WebSocket live stream")
ws_snapshot = threading.Event()
ws_telemetry = threading.Event()
ws_error = []

def _ws_on_message(wsapp, message):
    try:
        data = json.loads(message)
        if data.get("type") == "snapshot":
            ws_snapshot.set()
        elif data.get("type") == "telemetry":
            ws_telemetry.set()
    except Exception:
        pass

def _ws_on_error(wsapp, err):
    ws_error.append(str(err))

def _ws_thread():
    wsapp = websocket.WebSocketApp(WS_URL,
        on_message=_ws_on_message, on_error=_ws_on_error)
    wsapp.run_forever(ping_timeout=3)

t = threading.Thread(target=_ws_thread, daemon=True)
t.start()
time.sleep(1)

got_snapshot = ws_snapshot.wait(timeout=5)
check("WebSocket sends snapshot on connect", got_snapshot)
got_telemetry = ws_telemetry.wait(timeout=8)
check("WebSocket streams live telemetry", got_telemetry,
      "no telemetry - is simulator running?" if not got_telemetry else "")


# ─── 5. On-chain contract reads ───────────────────────────────────────────────
print("\n[5] On-chain contract state")
try:
    import json as _json
    from pathlib import Path
    abi_path = Path("artifacts/contracts/DroneRegistry.sol/DroneRegistry.json")
    abi = _json.loads(abi_path.read_text())["abi"]
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT), abi=abi)

    count = contract.functions.getDroneCount().call()
    check("getDroneCount() > 0", count > 0, f"{count} registered drones")

    if drones:
        logs_chain = contract.functions.getPassageLogs(drones[0]["droneId"]).call()
        check(f"getPassageLogs({drones[0]['droneId']}) readable", True,
              f"{len(logs_chain)} passage(s)")
except Exception as e:
    check("Contract read", False, str(e))


# ─── Summary ──────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok in results if ok)
total  = len(results)
print(f"\n{'─'*50}")
print(f"  Result: {passed}/{total} checks passed")
if passed == total:
    print(f"  \033[92mAll systems nominal - full pipeline verified.\033[0m")
else:
    failed = [label for label, ok in results if not ok]
    print(f"  \033[91mFailed:\033[0m {', '.join(failed)}")
print(f"{'─'*50}\n")

sys.exit(0 if passed == total else 1)
