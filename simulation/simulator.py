"""
simulator.py - Drone Mesh Tracker Kolkata Simulation
-----------------------------------------------------
Runs 3 simulated drones over Kolkata flight corridors.
Each drone:
  1. Publishes real-time telemetry to an MQTT broker every tick.
  2. Calls logPassage() on the DroneRegistry smart contract whenever
     it comes within NODE_TRIGGER_RADIUS_KM of a mesh node.

Prerequisites:
  - Mosquitto MQTT broker running on localhost:1883
      Windows: https://mosquitto.org/download/
      Start:   net start mosquitto  (or run mosquitto.exe)
  - Hardhat local node running:
      npx hardhat node
  - DroneRegistry deployed:
      npx hardhat run scripts/deploy.js --network localhost
"""

import json
import logging
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from web3 import Web3

# Allow running from inside the simulation/ folder directly
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ARTIFACTS_PATH,
    CONTRACT_ADDRESS,
    DEPLOYER_PRIVATE_KEY,
    MQTT_BROKER,
    MQTT_PORT,
    NODE_TRIGGER_RADIUS_KM,
    RPC_URL,
    TICK_INTERVAL,
)
from drone import Drone
from nodes import NODES
from paths import PATHS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Blockchain helpers ──────────────────────────────────────────────────────

def load_contract(w3: Web3):
    raw = json.loads(Path(ARTIFACTS_PATH).read_text())
    abi = raw["abi"]
    return w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=abi,
    )


class ChainClient:
    """Wraps Web3 interactions, fetching a fresh nonce before every transaction."""

    def __init__(self, w3: Web3, private_key: str):
        self.w3      = w3
        self.account = w3.eth.account.from_key(private_key)

    def _send(self, fn_call):
        nonce     = self.w3.eth.get_transaction_count(self.account.address, "pending")
        # Estimate gas and add 20% buffer to handle edge cases without overpaying.
        estimated = fn_call.estimate_gas({"from": self.account.address})
        gas_limit = int(estimated * 1.2)

        # EIP-1559 pricing: set max fees instead of legacy gasPrice.
        base_fee  = self.w3.eth.get_block("latest")["baseFeePerGas"]
        priority  = self.w3.to_wei(1, "gwei")   # 1 gwei tip to validators
        max_fee   = base_fee * 2 + priority      # comfortable ceiling above base fee

        tx = fn_call.build_transaction({
            "from":                 self.account.address,
            "nonce":                nonce,
            "gas":                  gas_limit,
            "maxFeePerGas":         max_fee,
            "maxPriorityFeePerGas": priority,
        })
        signed  = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=10)
        return tx_hash

    def register_drone(self, contract, drone_id: str) -> bool:
        """Register drone; silently skips if already registered."""
        try:
            tx_hash = self._send(
                contract.functions.registerDrone(drone_id, self.account.address)
            )
            log.info(f"[CHAIN] Registered {drone_id} | tx: {tx_hash.hex()[:14]}…")
            return True
        except Exception as e:
            if "already registered" in str(e):
                log.info(f"[CHAIN] {drone_id} already registered - skipping")
            else:
                log.warning(f"[CHAIN] Register {drone_id} failed: {e}")
            return False

    def log_passage(self, contract, drone_id: str, node_id: str, lat: float, lon: float):
        try:
            tx_hash = self._send(
                contract.functions.logPassage(
                    drone_id,
                    node_id,
                    int(lat * 1_000_000),
                    int(lon * 1_000_000),
                )
            )
            log.info(
                f"[CHAIN] {drone_id} → {node_id} logged | tx: {tx_hash.hex()[:14]}…"
            )
        except Exception as e:
            log.warning(f"[CHAIN] logPassage failed for {drone_id}/{node_id}: {e}")


# ─── Simulation ──────────────────────────────────────────────────────────────

def run():
    # ── MQTT ──
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        log.info(f"MQTT connected → {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        log.error(
            f"MQTT connection failed: {e}\n"
            "Is Mosquitto running? (Windows: 'net start mosquitto'  or  run mosquitto.exe)"
        )
        return

    # ── Web3 ──
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        log.error(
            "Web3 connection failed.\n"
            "Make sure the Hardhat node is running: npx hardhat node"
        )
        mqtt_client.loop_stop()
        return

    chain    = ChainClient(w3, DEPLOYER_PRIVATE_KEY)
    contract = load_contract(w3)
    log.info(f"Web3 connected → {RPC_URL} | deployer: {chain.account.address}")

    # ── Register drones on-chain ──
    drone_ids = ["DMT-KOL-01", "DMT-KOL-02", "DMT-KOL-03"]
    for drone_id in drone_ids:
        chain.register_drone(contract, drone_id)

    # ── Spawn one drone per route ──
    route_names = list(PATHS.keys())
    drones = [
        Drone(drone_ids[0], route_names[0], PATHS[route_names[0]]["waypoints"]),
        Drone(drone_ids[1], route_names[1], PATHS[route_names[1]]["waypoints"]),
        Drone(drone_ids[2], route_names[2], PATHS[route_names[2]]["waypoints"]),
    ]

    log.info("=" * 60)
    log.info("Simulation started - 3 drones flying over Kolkata")
    for name, path in PATHS.items():
        log.info(f"  {name}: {path['description']}")
    log.info(f"Mesh nodes active: {len(NODES)}")
    log.info("=" * 60)

    # ── Main loop ──
    while any(not d.finished for d in drones):
        for drone in drones:
            if drone.finished:
                continue

            drone.step(TICK_INTERVAL)

            # Publish telemetry over MQTT
            payload = json.dumps({
                "drone_id":  drone.drone_id,
                "route":     drone.route_name,
                "lat":       round(drone.lat, 7),
                "lon":       round(drone.lon, 7),
                "timestamp": time.time(),
            })
            mqtt_client.publish(f"drone/{drone.drone_id}/telemetry", payload, qos=0)

            # Check node proximity → write passage to blockchain
            triggered = drone.check_node_proximity(NODES, NODE_TRIGGER_RADIUS_KM)
            for node_id in triggered:
                node = NODES[node_id]
                log.info(
                    f"[NODE] {drone.drone_id} passed {node_id} "
                    f"({node['name']}) at ({drone.lat:.5f}, {drone.lon:.5f})"
                )
                chain.log_passage(contract, drone.drone_id, node_id, drone.lat, drone.lon)

        time.sleep(TICK_INTERVAL)

    log.info("All drones have completed their routes.")
    log.info(f"Total on-chain passage logs: check with 'npx hardhat console --network localhost'")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == "__main__":
    run()
