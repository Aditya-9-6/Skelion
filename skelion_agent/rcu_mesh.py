import threading
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger("skelion_agent.rcu_mesh")


class RCUEpochTracker:
    """
    Tracks active reader epochs across worker threads for deferred memory reclamation.
    """

    def __init__(self):
        self._global_epoch = 0
        self._reader_epochs: Dict[int, int] = {}
        self._lock = threading.Lock()

    def enter_epoch(self) -> int:
        thread_id = threading.get_ident()
        with self._lock:
            epoch = self._global_epoch
            self._reader_epochs[thread_id] = epoch
            return epoch

    def exit_epoch(self) -> None:
        thread_id = threading.get_ident()
        with self._lock:
            self._reader_epochs.pop(thread_id, None)

    def advance_epoch(self) -> int:
        with self._lock:
            self._global_epoch += 1
            return self._global_epoch

    def min_active_epoch(self) -> int:
        with self._lock:
            if not self._reader_epochs:
                return self._global_epoch
            return min(self._reader_epochs.values())


class RCURoutingTable:
    """
    Lock-free Read-Copy-Update (RCU) Sentinel Mesh routing table for agents.
    Readers access routing metadata completely lock-free with zero overhead.
    Writers duplicate, modify, and swap table pointers atomically.
    """

    def __init__(self):
        self._table_pointer: Dict[str, Any] = {}
        self._epoch_tracker = RCUEpochTracker()
        self._writer_lock = threading.Lock()
        self._reclamation_queue: List[Tuple[int, Dict[str, Any]]] = []

    def lookup(self, route_key: str) -> Optional[Any]:
        """
        Extremely fast, lock-free read path. Zero locks acquired during standard lookups.
        """
        self._epoch_tracker.enter_epoch()
        try:
            current_table = self._table_pointer
            return current_table.get(route_key)
        finally:
            self._epoch_tracker.exit_epoch()

    def get_all_routes(self) -> Dict[str, Any]:
        """
        Returns a shallow copy of the current route table snapshot under an epoch.
        """
        self._epoch_tracker.enter_epoch()
        try:
            return dict(self._table_pointer)
        finally:
            self._epoch_tracker.exit_epoch()

    def update_route(self, route_key: str, route_data: Any) -> None:
        """
        Thread-safe write path: copies current table, applies mutation, and atomically swaps pointer.
        Stale table is scheduled for epoch-based reclamation.
        """
        with self._writer_lock:
            old_table = self._table_pointer
            new_table = dict(old_table)
            new_table[route_key] = route_data

            # Atomic publish
            self._table_pointer = new_table

            # Advance global epoch and queue old table for reclamation
            retired_epoch = self._epoch_tracker.advance_epoch()
            self._reclamation_queue.append((retired_epoch, old_table))
            self._reclaim()

    def remove_route(self, route_key: str) -> bool:
        """
        Removes a route using RCU copy-on-write semantics.
        """
        with self._writer_lock:
            old_table = self._table_pointer
            if route_key not in old_table:
                return False
            new_table = dict(old_table)
            del new_table[route_key]

            self._table_pointer = new_table
            retired_epoch = self._epoch_tracker.advance_epoch()
            self._reclamation_queue.append((retired_epoch, old_table))
            self._reclaim()
            return True

    def _reclaim(self) -> None:
        """
        Reclaims stale tables whose retired epoch is older than all active reader epochs.
        """
        min_epoch = self._epoch_tracker.min_active_epoch()
        retained = []
        for retired_epoch, table in self._reclamation_queue:
            if retired_epoch < min_epoch:
                # Safe to reclaim/garbage collect
                del table
            else:
                retained.append((retired_epoch, table))
        self._reclamation_queue = retained
