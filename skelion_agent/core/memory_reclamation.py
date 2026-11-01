import threading
import atomic
from typing import List, Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EpochManager:
    """
    Epoch-based memory reclamation (Hazard Pointer / Epoch-based GC variant)
    for lock-free data structures in Skelion Core. Prevents use-after-free conditions
    during concurrent traversals without global stop-the-world pauses.
    """
    def __init__(self, num_threads: int = 64):
        self.global_epoch = atomic.AtomicLong(0)
        # Thread local or array of thread epoch reservations
        self._thread_epochs: List[atomic.AtomicLong] = [
            atomic.AtomicLong(0) for _ in range(num_threads)
        ]
        self._retired_lists: List[List[tuple]] = [[] for _ in range(3)]
        self._lock = threading.Lock()

    def enter(self, thread_id: int) -> int:
        """Mark entry into a critical section for a given thread."""
        current = self.global_epoch.load()
        self._thread_epochs[thread_id % len(self._thread_epochs)].store(current)
        return current

    def leave(self, thread_id: int) -> None:
        """Mark exit from a critical section by setting epoch to inactive (0 or sentinel)."""
        self._thread_epochs[thread_id % len(self._thread_epochs)].store(0)

    def retire(self, obj: Any, destructor: Callable[[Any], None], epoch: int) -> None:
        """Retire an object for deferred reclamation when all threads pass the epoch."""
        with self._lock:
            list_idx = epoch % 3
            self._retired_lists[list_idx].append((obj, destructor))

    def advance(self) -> None:
        """Attempt to advance the global epoch and reclaim safe generations."""
        with self._lock:
            min_epoch = self.global_epoch.load()
            for t_epoch in self._thread_epochs:
                val = t_epoch.load()
                if val != 0 and val < min_epoch:
                    min_epoch = val

            target_global = self.global_epoch.load()
            if min_epoch >= target_global:
                new_epoch = target_global + 1
                self.global_epoch.store(new_epoch)
                # Reclaim oldest retired list
                reclaim_idx = (new_epoch - 2) % 3
                to_free = self._retired_lists[reclaim_idx]
                self._retired_lists[reclaim_idx] = []
                for obj, destructor in to_free:
                    try:
                        destructor(obj)
                    except Exception as e:
                        logger.error(f"Error during deferred object reclamation: {e}")
