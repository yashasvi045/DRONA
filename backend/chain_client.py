"""
chain_client.py - Read-only Web3 client for DroneRegistry.

All functions are synchronous (called from FastAPI route handlers via
asyncio.to_thread so they don't block the event loop).
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from web3 import Web3

log = logging.getLogger(__name__)

RPC_URL          = os.getenv("RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = os.getenv(
    "CONTRACT_ADDRESS",
    "0x5FbDB2315678afecb367f032d93F642f64180aa3",
)
ARTIFACTS_PATH = (
    Path(__file__).parent.parent
    / "artifacts" / "contracts" / "DroneRegistry.sol" / "DroneRegistry.json"
)


def _get_contract():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to node at {RPC_URL}")
    raw = json.loads(ARTIFACTS_PATH.read_text())
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=raw["abi"],
    )
    return w3, contract


def get_all_drones() -> list[dict]:
    """Return all registered drones from the contract."""
    try:
        _, contract = _get_contract()
        count = contract.functions.getDroneCount().call()
        drones = []
        for i in range(count):
            drone_id = contract.functions.registeredDroneIds(i).call()
            drone    = contract.functions.drones(drone_id).call()
            drones.append({
                "droneId":      drone[0],
                "owner":        drone[1],
                "isActive":     drone[2],
                "registeredAt": drone[3],
            })
        return drones
    except Exception as e:
        log.error(f"get_all_drones failed: {e}")
        return []


def get_drone(drone_id: str) -> Optional[dict]:
    """Return a single drone's on-chain record."""
    try:
        _, contract = _get_contract()
        drone = contract.functions.drones(drone_id).call()
        if not drone[0]:
            return None
        return {
            "droneId":      drone[0],
            "owner":        drone[1],
            "isActive":     drone[2],
            "registeredAt": drone[3],
        }
    except Exception as e:
        log.error(f"get_drone({drone_id}) failed: {e}")
        return None


def get_passage_logs(drone_id: str) -> list[dict]:
    """Return all passage logs for a drone from the contract."""
    try:
        _, contract = _get_contract()
        logs = contract.functions.getPassageLogs(drone_id).call()
        return [
            {
                "droneId":   entry[0],
                "nodeId":    entry[1],
                "lat":       entry[2] / 1_000_000,
                "lon":       entry[3] / 1_000_000,
                "timestamp": entry[4],
            }
            for entry in logs
        ]
    except Exception as e:
        log.error(f"get_passage_logs({drone_id}) failed: {e}")
        return []
