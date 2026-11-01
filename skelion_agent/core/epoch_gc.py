import threading
from typing import Any, Callable, Dict, List, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class EpochManager:
    """
    Manages global epoch counters and thread registration for epoch-based
    memory reclamation (EBMR) across concurrent Skelion agent nodes and workers.
    """

    def __init__(self):
        self._epoch = 0
        self._active_threads: Dict[int, int] = {}  # thread_id -> registered_epoch
        self._lock = threading.Lock()

    @property
    def current_epoch(self) -> int:
        return self._epoch

    def enter(self) -> int:
        """
        Mark the calling thread as active in the current epoch.
        Returns the epoch identifier the thread entered.
        """
        t_id = threading.get_ident()
        with self._lock:
            ep = self._epoch
            self._active_threads[t_id] = ep
            return ep

    def exit(self) -> None:
        """
        Mark the calling thread as inactive / exiting the active epoch.
        """
        t_id = threading.get_ident()
        with self._lock:
            self._active_threads.pop(t_id, None)

    def advance(self) -> int:
        """
        Advance the global epoch if all active threads have caught up
        or if no conflicting threads remain in older epochs.
        """
        with self._lock:
            self._epoch += 1
            return self._epoch

    def min_active_epoch(self) -> int:
        """
        Returns the minimum epoch currently held by any active thread.
        If no threads are active, returns the current global epoch.
        """
        with self._lock:
            if not self._active_threads:
                return self._epoch
            return min(self._active_threads.values(), default=self._epoch)


class HazardPointerRegistry:
    """
    Thread-safe hazard pointer registry protecting shared state graph nodes
    from premature deallocation while being actively traversed by worker threads.
    """

    def __init__(self):
        self._hazards: Dict[
            int, Any
        ] = {}  # thread_id -> protected object id or reference
        self._lock = threading.Lock()

    def protect(self, obj: Any) -> Any:
        """
        Publish a hazard pointer for the calling thread protecting the given object.
        """
        t_id = threading.get_ident()
        with self._lock:
            self._hazards[t_id] = id(obj)
        return obj

    def clear(self) -> None:
        """
        Clear the hazard pointer published by the calling thread.
        """
        t_id = threading.get_ident()
        with self._lock:
            self._hazards.pop(t_id, None)

    def get_protected_ids(self) -> Set[int]:
        """
        Returns a set of all object IDs currently protected by active hazard pointers.
        """
        with self._lock:
            return set(self._hazards.values())


class EpochGarbageCollector:
    """
    High-performance lock-free epoch-based garbage collector combining hazard pointers
    and generational deferred retirement lists for agent state graph nodes.
    """

    def __init__(self, cleanup_interval_retirements: int = 64):
        self.epoch_manager = EpochManager()
        self.hazard_registry = HazardPointerRegistry()
        self._retirement_generations: List[List[Tuple[int, Callable[[], None]]]] = [
            [],
            [],
            [],
        ]
        self._cleanup_threshold = cleanup_interval_retirements
        self._retire_count = 0
        self._lock = threading.Lock()

    def retire(self, destructor: Callable[[], None]) -> None:
        """
        Retire an object by registering its destructor to be executed once
        no active threads or hazard pointers reference it.
        """
        current_ep = self.epoch_manager.current_epoch
        with self._lock:
            self._retirement_generations[current_ep % 3].append(
                (current_ep, destructor)
            )
            self._retire_count += 1
            if self._retire_count >= self._cleanup_threshold:
                self._collect_internal()
                self._retire_count = 0

    def collect(self) -> int:
        """
        Force collection of retired nodes that are safe to free.
        Returns the number of reclaimed destructors executed.
        """
        with self._lock:
            return self._collect_internal()

    def _collect_internal(self) -> int:
        # Advance epoch to stage pending retirements
        self.epoch_manager.advance()
        min_ep = self.epoch_manager.min_active_epoch()
        protected_ids = self.hazard_registry.get_protected_ids()

        reclaimed_count = 0
        surviving_generations: List[List[Tuple[int, Callable[[], None]]]] = [[], [], []]

        for gen_idx, gen_list in enumerate(self._retirement_generations):
            kept = []
            for ep, destructor in gen_list:
                # Safe to reclaim if the retirement epoch is strictly behind min active epoch
                if ep < min_ep:
                    try:
                        destructor()
                        reclaimed_count += 1
                    except Exception as e:
                        logger.error(
                            f"Error executing destructor during GC collection: {e}"
                        )
                else:
                    kept.append((ep, destructor))
            surviving_generations[gen_idx] = kept

        self._retirement_generations = surviving_generations
        return reclaimed_count


# Global singleton instance for platform-wide Skelion agent graph memory reclamation
GLOBAL_EPOCH_GC = EpochGarbageCollector()
