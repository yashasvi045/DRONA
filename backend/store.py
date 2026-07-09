"""
store.py - Thread-safe in-memory position store.

Acts as a lightweight Redis substitute for local dev.
Swap out `PositionStore` for a Redis client in production without
changing any other backend code.
"""

import threading
from typing import Optional


class PositionStore:
    """
    Stores the latest telemetry payload for each drone.
    All methods are thread-safe (MQTT callback runs on a different thread).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._positions: dict[str, dict] = {}

    def update(self, drone_id: str, payload: dict) -> None:
        with self._lock:
            self._positions[drone_id] = payload

    def get(self, drone_id: str) -> Optional[dict]:
        with self._lock:
            return self._positions.get(drone_id)

    def all(self) -> dict[str, dict]:
        with self._lock:
            return dict(self._positions)


# Singleton used across the whole backend process
store = PositionStore()
