"""
ws_manager.py - WebSocket connection manager.

Tracks all active WebSocket clients and provides a broadcast method.
Called from the asyncio event loop only - no locking needed.
"""

import json
import logging
from fastapi import WebSocket

log = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)
        log.info(f"WebSocket client connected  (total: {len(self._clients)})")

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.remove(ws)
        log.info(f"WebSocket client disconnected (total: {len(self._clients)})")

    async def broadcast(self, payload: dict) -> None:
        """Send a JSON payload to all connected clients, dropping dead connections."""
        if not self._clients:
            return
        message = json.dumps(payload)
        dead = []
        for client in self._clients:
            try:
                await client.send_text(message)
            except Exception:
                dead.append(client)
        for client in dead:
            self._clients.remove(client)


# Singleton
manager = WebSocketManager()
