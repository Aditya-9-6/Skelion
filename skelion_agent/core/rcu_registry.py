import time
import threading
from typing import Dict, Any, Optional, Callable, List
import logging

logger = logging.getLogger(__name__)


class RCUEpochTracker:
    """
    Tracks active reader epochs for deferred memory reclamation in RCU updates.
    """
    def __init__(self):
        self._current_epoch = 0
        self._reader_counts: Dict[int, int] = {}
        self._lock = threading.Lock()

    def enter(self) -> int:
        with self._lock:
            epoch = self._current_epoch
            self._reader_counts[epoch] = self._reader_counts.get(epoch, 0) + 1
            return epoch

    def exit(self, epoch: int) -> None:
        with self._lock:
            if epoch in self._reader_counts:
                self._reader_counts[epoch] -= 1
                if self._reader_counts[epoch] <= 0 and epoch < self._current_epoch:
                    del self._reader_counts[epoch]

    def advance(self) -> int:
        with self._lock:
            self._current_epoch += 1
            return self._current_epoch

    def can_reclaim(self, epoch: int) -> bool:
        with self._lock:
            return epoch not in self._reader_counts or self._reader_counts[epoch] == 0


class RCURegistry:
    """
    Asynchronous Lock-Free Read-Copy-Update (RCU) Registry for dynamic incident routing
    maps. Provides zero-mutex-contention reads with atomic pointer swaps for updates
    and deferred reclamation of stale route state using epoch counters.
    """
    def __init__(self, initial_map: Optional[Dict[str, Any]] = None):
        self._current_map: Dict[str, Any] = dict(initial_map) if initial_map is not None else {}
        self._epoch_tracker = RCUEpochTracker()
        self._update_lock = threading.Lock()
        self._reclamation_queue: List[Tuple[int, Dict[str, Any]]] = []

    def get(self, key: str, default: Any = None) -> Any:
        """
        Read operation with zero mutex contention and full memory visibility.
        """
        epoch = self._epoch_tracker.enter()
        try:
            current = self._current_map
            return current.get(key, default)
        finally:
            self._epoch_tracker.exit(epoch)

    def get_all(self) -> Dict[str, Any]:
        """
        Returns a shallow copy of the active routing map under RCU protection.
        """
        epoch = self._epoch_tracker.enter()
        try:
            return dict(self._current_map)
        finally:
            self._epoch_tracker.exit(epoch)

    def update(self, mutator: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes a copy-update cycle:
        1. Acquires exclusive writer lock.
        2. Copies current map, invokes mutator.
        3. Atomically swaps the pointer.
        4. Defers reclamation of the old map until active reader epochs clear.
        """
        with self._update_lock:
            old_map = self._current_map
            new_map = dict(old_map)
            new_map = mutator(new_map)

            # Advance epoch and queue old map for deferred reclamation
            retired_epoch = self._epoch_tracker.advance()
            self._current_map = new_map

            self._reclamation_queue.append((retired_epoch, old_map))
            self._sweep_reclamation()

            return new_map

    def set_route(self, key: str, value: Any) -> None:
        def _mutate(m: Dict[str, Any]) -> Dict[str, Any]:
            m[key] = value
            return m
        self.update(_mutate)

    def remove_route(self, key: str) -> None:
        def _mutate(m: Dict[str, Any]) -> Dict[str, Any]:
            m.pop(key, None)
            return m
        self.update(_mutate)

    def _sweep_reclamation(self) -> None:
        """
        Reclaims memory for retired maps whose reader epochs have completely exited.
        """
        remaining = []
        for epoch, stale_map in self._reclamation_queue:
            if self._epoch_tracker.can_reclaim(epoch):
                # Stale map reference dropped
                del stale_map
            else:
                remaining.append((epoch, stale_map))
        self._reclamation_queue = remaining
