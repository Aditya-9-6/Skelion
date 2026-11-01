import asyncio
from collections import deque
from typing import Any, Deque, List, Optional


class BoundedFIFOChannelTracker:
    """Tracks in-flight asyncio network messages across bounded FIFO channels for Chandy-Lamport snapshotting."""

    def __init__(self, channel_id: str, max_capacity: int = 10000) -> None:
        self.channel_id = channel_id
        self.max_capacity = max_capacity
        self._messages: Deque[Any] = deque()
        self._recording = False
        self._recorded_messages: List[Any] = []
        self._lock = asyncio.Lock()

    async def send(self, message: Any) -> bool:
        async with self._lock:
            if len(self._messages) >= self.max_capacity:
                return False
            self._messages.append(message)
            if self._recording:
                self._recorded_messages.append(message)
            return True

    async def receive(self) -> Optional[Any]:
        async with self._lock:
            if not self._messages:
                return None
            return self._messages.popleft()

    async def start_recording(self) -> None:
        async with self._lock:
            self._recording = True
            self._recorded_messages = []

    async def stop_recording(self) -> List[Any]:
        async with self._lock:
            self._recording = False
            recorded = list(self._recorded_messages)
            self._recorded_messages = []
            return recorded

    async def clear(self) -> None:
        async with self._lock:
            self._messages.clear()
            self._recorded_messages.clear()
            self._recording = False
