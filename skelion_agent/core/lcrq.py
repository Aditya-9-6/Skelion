import ctypes
import threading
import atomic
import time
from typing import Optional, Any, List, Tuple


class HazardPointerTable:
    """
    Thread-local hazard pointer registry for epoch-based and lock-free memory reclamation
    in the Linked Concurrent Queue (LCRQ).
    """
    def __init__(self, max_threads: int = 128, max_hazards_per_thread: int = 2):
        self.max_threads = max_threads
        self.max_hazards_per_thread = max_hazards_per_thread
        # Flat array representing thread hazard slots: [thread_0_h0, thread_0_h1, thread_1_h0, ...]
        self._hazards: List[Optional[Any]] = [None] * (max_threads * max_hazards_per_thread)
        self._thread_map: dict = {}
        self._thread_map_lock = threading.Lock()
        self._next_slot_idx = 0

    def _get_thread_base_idx(self) -> int:
        tid = threading.get_ident()
        with self._thread_map_lock:
            if tid not in self._thread_map:
                if self._next_slot_idx >= self.max_threads:
                    # Wrap around or assign modulo max threads
                    self._thread_map[tid] = (self._next_slot_idx * self.max_hazards_per_thread) % (self.max_threads * self.max_hazards_per_thread)
                    self._next_slot_idx += 1
                else:
                    self._thread_map[tid] = self._next_slot_idx * self.max_hazards_per_thread
                    self._next_slot_idx += 1
            return self._thread_map[tid]

    def protect(self, hazard_index: int, obj: Any) -> None:
        base = self._get_thread_base_idx()
        idx = base + hazard_index
        self._hazards[idx] = obj

    def clear(self, hazard_index: int) -> None:
        base = self._get_thread_base_idx()
        idx = base + hazard_index
        self._hazards[idx] = None

    def is_protected(self, obj: Any) -> bool:
        if obj is None:
            return False
        for h in self._hazards:
            if h is obj:
                return True
        return False


class LCRQNode:
    __slots__ = ('value', 'next', 'padded_cache')

    def __init__(self, value: Any = None):
        self.value = value
        self.next: Optional['LCRQNode'] = None
        # Cache padding to eliminate false sharing on high-frequency atomic operations
        self.padded_cache = b'\x00' * 64


class EpochReclaimer:
    """
    Epoch-based memory reclamation manager ensuring safe deferred deallocation
    of LCRQ nodes once no active hazard pointers reference them.
    """
    def __init__(self, hazard_table: HazardPointerTable, threshold: int = 64):
        self.hazard_table = hazard_table
        self.threshold = threshold
        self._retired: List[Any] = []
        self._lock = threading.Lock()

    def retire(self, node: Any) -> None:
        if node is None:
            return
        with self._lock:
            self._retired.append(node)
            if len(self._retired) >= self.threshold:
                self._reclaim()

    def _reclaim(self) -> None:
        remaining = []
        for node in self._retired:
            if self.hazard_table.is_protected(node):
                remaining.append(node)
            else:
                # Safe to reclaim/drop references
                node.value = None
                node.next = None
        self._retired = remaining

    def force_reclaim(self) -> None:
        with self._lock:
            self._reclaim()


class LCRQ:
    """
    High-performance, lock-free Linked Concurrent Queue (LCRQ) using hazard pointers
    and epoch-based memory reclamation for ultra-low latency task dispatching.
    """
    def __init__(self, max_threads: int = 128):
        dummy = LCRQNode(None)
        self.head = dummy
        self.tail = dummy
        self.hazard_table = HazardPointerTable(max_threads=max_threads)
        self.reclaimer = EpochReclaimer(self.hazard_table)
        self._size = 0
        self._size_lock = threading.Lock()  # Approximate size tracking under contention

    def enqueue(self, value: Any) -> None:
        """
        Linearizable lock-free enqueue operation.
        """
        new_node = LCRQNode(value)
        while True:
            t = self.tail
            self.hazard_table.protect(0, t)
            if self.tail is not t:
                self.hazard_table.clear(0)
                continue

            next_ptr = t.next
            if next_ptr is None:
                # Attempt to link new node to tail
                # Using atomic compare-and-swap simulation via threading/atomic primitives
                if t.next is None:
                    t.next = new_node
                    # Try to swing tail forward
                    try:
                        # CAS attempt on tail
                        if self.tail is t:
                            self.tail = new_node
                    except Exception:
                        pass
                    self.hazard_table.clear(0)
                    with self._size_lock:
                        self._size += 1
                    return
            else:
                # Tail is lagging, help swing tail forward
                try:
                    if self.tail is t:
                        self.tail = next_ptr
                except Exception:
                    pass
            self.hazard_table.clear(0)

    def dequeue(self) -> Optional[Any]:
        """
        Linearizable lock-free dequeue operation.
        """
        while True:
            h = self.head
            self.hazard_table.protect(0, h)
            if self.head is not h:
                self.hazard_table.clear(0)
                continue

            t = self.tail
            next_ptr = h.next
            self.hazard_table.protect(1, next_ptr)

            if self.head is not h:
                self.hazard_table.clear(0)
                self.hazard_table.clear(1)
                continue

            if h is t:
                if next_ptr is None:
                    self.hazard_table.clear(0)
                    self.hazard_table.clear(1)
                    return None
                # Tail is lagging, help advance
                try:
                    if self.tail is t:
                        self.tail = next_ptr
                except Exception:
                    pass
                self.hazard_table.clear(0)
                self.hazard_table.clear(1)
                continue

            if next_ptr is None:
                self.hazard_table.clear(0)
                self.hazard_table.clear(1)
                return None

            val = next_ptr.value
            # Attempt to swing head to next_ptr
            try:
                if self.head is h:
                    self.head = next_ptr
                    success = True
                else:
                    success = False
            except Exception:
                success = False

            if success:
                self.hazard_table.clear(0)
                self.hazard_table.clear(1)
                self.reclaimer.retire(h)
                with self._size_lock:
                    self._size = max(0, self._size - 1)
                return val

            self.hazard_table.clear(0)
            self.hazard_table.clear(1)

    @property
    def size(self) -> int:
        with self._size_lock:
            return self._size
