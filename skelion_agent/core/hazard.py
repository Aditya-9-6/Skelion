import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class ThreadHazardState:
    __slots__ = ("thread_id", "epoch", "hazard_pointers", "retired_list")

    def __init__(self, thread_id: int, max_hazards: int = 4):
        self.thread_id = thread_id
        self.epoch: int = 0
        self.hazard_pointers: List[Optional[Any]] = [None] * max_hazards
        self.retired_list: List[Tuple[Any, Callable[[Any], None]]] = []


class HazardPointerManager:
    """
    High-performance lock-free epoch-based reclamation hazard pointer engine
    designed for managing concurrent shared state and telemetry buffers in Skelion's
    agent mesh without blocking reader threads.
    """

    def __init__(self, max_hazards_per_thread: int = 4, scan_threshold: int = 64):
        self.max_hazards = max_hazards_per_thread
        self.scan_threshold = scan_threshold
        self._global_epoch = 0
        self._threads: Dict[int, ThreadHazardState] = {}
        self._lock = (
            threading.Lock()
        )  # Used strictly for registration/cleanup bookkeeping

    def _get_thread_state(self) -> ThreadHazardState:
        tid = threading.get_ident()
        state = self._threads.get(tid)
        if state is None:
            with self._lock:
                state = self._threads.get(tid)
                if state is None:
                    state = ThreadHazardState(tid, self.max_hazards)
                    state.epoch = self._global_epoch
                    self._threads[tid] = state
        return state

    def acquire(self, obj: Any, index: int = 0) -> Any:
        """
        Publish an object reference to the current thread's hazard pointer array.
        Returns the object for fluent usage.
        """
        state = self._get_thread_state()
        if index < 0 or index >= self.max_hazards:
            raise IndexError(
                f"Hazard pointer index {index} out of bounds (max: {self.max_hazards})"
            )
        state.hazard_pointers[index] = obj
        return obj

    def release(self, index: int = 0) -> None:
        """
        Clear a hazard pointer slot for the current thread.
        """
        state = self._get_thread_state()
        if index < 0 or index >= self.max_hazards:
            raise IndexError(
                f"Hazard pointer index {index} out of bounds (max: {self.max_hazards})"
            )
        state.hazard_pointers[index] = None

    def retire(self, obj: Any, deleter: Callable[[Any], None]) -> None:
        """
        Retire an object, deferring its destruction until no thread holds a hazard
        pointer referencing it.
        """
        state = self._get_thread_state()
        state.retired_list.append((obj, deleter))

        if len(state.retired_list) >= self.scan_threshold:
            self._reclaim(state)

    def advance_epoch(self) -> int:
        """
        Advance the global epoch counter to coordinate barrier synchronization.
        """
        with self._lock:
            self._global_epoch += 1
            new_epoch = self._global_epoch

        state = self._get_thread_state()
        state.epoch = new_epoch
        return new_epoch

    def _reclaim(self, state: ThreadHazardState) -> None:
        """
        Scan all active thread hazard pointers and reclaim safe retired objects.
        """
        # Collect all currently protected hazard pointers across all threads
        protected: Set[int] = set()
        with self._lock:
            thread_states = list(self._threads.values())

        for t_state in thread_states:
            for hp in t_state.hazard_pointers:
                if hp is not None:
                    protected.add(id(hp))

        remaining_retired = []
        for obj, deleter in state.retired_list:
            if id(obj) not in protected:
                try:
                    deleter(obj)
                except Exception as e:
                    logger.error(f"Error executing deferred object destructor: {e}")
            else:
                remaining_retired.append((obj, deleter))

        state.retired_list = remaining_retired

    def force_reclaim_all(self) -> int:
        """
        Force full reclamation across all threads. Returns the count of remaining active retired items.
        """
        total_remaining = 0
        with self._lock:
            thread_states = list(self._threads.values())

        for state in thread_states:
            self._reclaim(state)
            total_remaining += len(state.retired_list)

        return total_remaining
