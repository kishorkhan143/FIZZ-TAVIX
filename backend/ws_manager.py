"""
AuthSentinel — WebSocket Connection Manager
============================================
Tracks all active dashboard WebSocket connections and broadcasts messages.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("authsentinel.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket connected — total connections: %d", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections = [c for c in self._connections if c is not ws]
        logger.info("WebSocket disconnected — total connections: %d", len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a JSON-serializable dict to all connected dashboards."""
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []

        async with self._lock:
            targets = list(self._connections)

        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception as exc:
                logger.warning("Failed to send to WebSocket: %s", exc)
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
