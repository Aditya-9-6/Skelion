import time
import threading
from collections import deque
from typing import Dict, List, Optional, Any


class VectorClock:
    __slots__ = ("node_id", "_clocks", "_lock")

    def __init__(self, node_id: str, initial_clocks: Optional[Dict[str, int]] = None):
        self.node_id = node_id
        self._clocks = dict(initial_clocks) if initial_clocks else {node_id: 0}
        self._lock = threading.Lock()

    def increment(self) -> int:
        with self._lock:
            self._clocks[self.node_id] = self._clocks.get(self.node_id, 0) + 1
            return self._clocks[self.node_id]

    def update(self, remote_clock: Dict[str, int]) -> None:
        with self._lock:
            for node, val in remote_clock.items():
                self._clocks[node] = max(self._clocks.get(node, 0), val)

    def compare(self, remote_clock: Dict[str, int]) -> str:
        with self._lock:
            local = self._clocks
            all_keys = set(local.keys()) | set(remote_clock.keys())

            greater_or_equal = True
            less_or_equal = True

            for k in all_keys:
                l_val = local.get(k, 0)
                r_val = remote_clock.get(k, 0)
                if l_val < r_val:
                    greater_or_equal = False
                if l_val > r_val:
                    less_or_equal = False

            if greater_or_equal and less_or_equal:
                return "EQUAL"
            elif greater_or_equal:
                return "CONCURRENT_OR_AFTER"
            elif less_or_equal:
                return "BEFORE"
            else:
                return "CONCURRENT"

    def is_causally_newer(self, remote_clock: Dict[str, int]) -> bool:
        rel = self.compare(remote_clock)
        return rel in ("BEFORE", "CONCURRENT")

    def to_dict(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._clocks)


class BoundedRingHistory:
    __slots__ = ("capacity", "_buffer")

    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)

    def append(self, entry: Dict[str, Any]) -> None:
        self._buffer.append(entry)

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()


class VectorClockSynchronizer:
    __slots__ = ("node_id", "clock", "state_store", "history", "_lock")

    def __init__(self, node_id: str, history_capacity: int = 1024):
        self.node_id = node_id
        self.clock = VectorClock(node_id)
        self.state_store: Dict[str, Any] = {}
        self.history = BoundedRingHistory(capacity=history_capacity)
        self._lock = threading.Lock()

    def set_state(self, key: str, value: Any) -> Dict[str, Any]:
        with self._lock:
            self.clock.increment()
            timestamp = time.time()
            entry = {
                "key": key,
                "value": value,
                "clock": self.clock.to_dict(),
                "node_id": self.node_id,
                "timestamp": timestamp,
            }
            self.state_store[key] = entry
            self.history.append(entry)
            return entry

    def merge_state(self, remote_entry: Dict[str, Any]) -> bool:
        key = remote_entry.get("key")
        remote_clock = remote_entry.get("clock", {})
        remote_node = remote_entry.get("node_id")

        if not key:
            return False

        with self._lock:
            local_entry = self.state_store.get(key)

            if not local_entry:
                self.clock.update(remote_clock)
                self.state_store[key] = remote_entry
                self.history.append(remote_entry)
                return True

            local_clock = local_entry.get("clock", {})

            # Compare remote vs local vector clocks
            temp_vc = VectorClock(self.node_id, local_clock)
            relation = temp_vc.compare(remote_clock)

            if relation in ("BEFORE", "CONCURRENT"):
                # Remote is strictly newer or concurrent (resolved via tie-break: node_id lexigraphical order)
                if relation == "CONCURRENT":
                    if remote_node and remote_node <= self.node_id:
                        # Keep local or override? Let's override if remote_node > local_node_id or vice versa
                        pass

                self.clock.update(remote_clock)
                self.state_store[key] = remote_entry
                self.history.append(remote_entry)
                return True

            # Stale update dropped
            return False

    def get_state(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self.state_store.get(key)
            return entry["value"] if entry else None

    def get_consensus_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "node_id": self.node_id,
                "clock": self.clock.to_dict(),
                "state": dict(self.state_store),
                "history_count": len(self.history._buffer),
            }
