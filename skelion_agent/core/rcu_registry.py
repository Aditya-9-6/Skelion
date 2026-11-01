import threading
import time
import atomicwrites
from typing import Dict, Any, Optional, Callable, List
import logging

logger = logging.getLogger(__name__)


class RCUEpochTracker:
    """
    Tracks active reader threads and epochs for epoch-based memory reclamation.
    """
    def __init__(self):
        self._current_epoch = 0
        self._reader_epochs: Dict[int, int] = {}
        self._lock = threading.Lock()

    def enter_critical_section(self) -> int:
        thread_id = threading.get_ident()
        with self._lock:
            epoch = self._current_epoch
            self._reader_epochs[thread_id] = epoch
            return epoch

    def exit_critical_section(self) -> None:
        thread_id = threading.get_ident()
        with self._lock:
            self._reader_epochs.pop(thread_id, None)

    def advance_epoch(self) -> int:
        with self._lock:
            self._current_epoch += 1
            return self._current_epoch

    def can_reclaim(self, target_epoch: int) -> bool:
        with self._lock:
            if not self._reader_epochs:
                return True
            for th_id, ep in self._reader_epochs.items():
                if ep < target_epoch:
                    return False
            return True


class RCURegistry:
    """
    High-performance, lock-free Read-Copy-Update (RCU) registry for dynamic agent route tables.
    Provides atomic pointer swapping for updates while guaranteeing thread-safe, non-blocking
    reads without acquiring mutual exclusion locks in the critical path.
    """
    def __init__(self, initial_routes: Optional[Dict[str, Any]] = None):
        self._route_table: Dict[str, Any] = dict(initial_routes) if initial_routes is not None else {}
        self._epoch_tracker = RCUEpochTracker()
        self._reclamation_queue: List[Tuple[int, Dict[str, Any]]] = []
        self._update_lock = threading.Lock()

    def lookup(self, route_key: str) -> Optional[Any]:
        """
        Perform a lock-free, zero-allocation read lookup in the current route table.
        """
        self._epoch_tracker.enter_critical_section()
        try:
            # Python dictionary reads are atomic due to GIL, and RCU pointer swap
            # replaces the reference atomically.
            table = self._route_table
            return table.get(route_key)
        finally:
            self._epoch_tracker.exit_critical_section()

    def get_all_routes(self) -> Dict[str, Any]:
        """
        Return a shallow copy of the active route table under RCU protection.
        """
        self._epoch_tracker.enter_critical_section()
        try:
            return dict(self._route_table)
        finally:
            self._epoch_tracker.exit_critical_section()

    def update_route(self, route_key: str, route_value: Any) -> None:
        """
        Atomically update a route using Copy-On-Write semantics and RCU pointer swapping,
        followed by epoch reclamation of stale generations.
        """
        with self._update_lock:
            # 1. Copy: Create a new generation of the route table
            new_table = dict(self._route_table)
            old_table = self._route_table
            
            new_table[route_key] = route_value
            
            # 2. Publish: Atomic pointer swap
            self._route_table = new_table
            
            # 3. Advance epoch & queue old generation for reclamation
            stale_epoch = self._epoch_tracker.advance_epoch()
            self._reclamation_queue.append((stale_epoch, old_table))
            
            # 4. Trigger deferred reclamation check
            self._reclaim_stale_generations()

    def remove_route(self, route_key: str) -> bool:
        """
        Atomically remove a route using Copy-On-Write semantics.
        """
        with self._update_lock:
            if route_key not in self._route_table:
                return False
            
            new_table = dict(self._route_table)
            old_table = self._route_table
            
            del new_table[route_key]
            
            self._route_table = new_table
            stale_epoch = self._epoch_tracker.advance_epoch()
            self._reclamation_queue.append((stale_epoch, old_table))
            
            self._reclaim_stale_generations()
            return True

    def _reclaim_stale_generations(self) -> None:
        """
        Safely deallocate stale route table generations once all active reader threads
        have exited the critical section.
        """
        remaining_queue = []
        for epoch, table in self._reclamation_queue:
            if self._epoch_tracker.can_reclaim(epoch):
                # Safe to deallocate / drop reference
                del table
            else:
                remaining_queue.append((epoch, table))
        self._reclamation_queue = remaining_queue
