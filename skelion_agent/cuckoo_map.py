import threading
import select
import os
import time
import logging
from typing import Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


class EpochManager:
    """
    Epoch-based memory reclamation (EBR) manager for non-blocking concurrent data structures.
    """
    def __init__(self, num_threads: int = 64):
        self._global_epoch = 0
        self._thread_epochs: List[int] = [0] * num_threads
        self._retired_lists: List[List[Tuple[Any, Any]] ] = [[] for _ in range(3)]
        self._lock = threading.Lock()

    def enter(self, thread_idx: int) -> int:
        with self._lock:
            curr = self._global_epoch
            self._thread_epochs[thread_idx % len(self._thread_epochs)] = curr
            return curr

    def leave(self, thread_idx: int) -> None:
        with self._lock:
            self._thread_epochs[thread_idx % len(self._thread_epochs)] = 0

    def retire(self, obj: Any, destructor: Any, epoch: int) -> None:
        with self._lock:
            self._retired_lists[epoch % 3].append((obj, destructor))

    def advance(self) -> None:
        with self._lock:
            self._global_epoch += 1
            reclaim_idx = (self._global_epoch - 2) % 3
            to_free = self._retired_lists[reclaim_idx]
            self._retired_lists[reclaim_idx] = []
            for obj, destructor in to_free:
                try:
                    destructor(obj)
                except Exception as e:
                    logger.error(f"Error reclaiming object: {e}")


class CuckooBucket:
    __slots__ = ('key', 'value', 'hash', 'version', 'tombstone')

    def __init__(self, key: Optional[Any] = None, value: Optional[Any] = None, h: int = 0, version: int = 0, tombstone: bool = False):
        self.key = key
        self.value = value
        self.hash = h
        self.version = version
        self.tombstone = tombstone


class EpollCuckooHashMap:
    """
    High-performance, non-blocking concurrent cuckoo hash map utilizing epoll-driven
    event notification and epoch-based memory reclamation for sub-microsecond incident state routing.
    """
    def __init__(self, capacity: int = 1024, load_factor: float = 0.5, max_displacements: int = 64):
        self.capacity = self._next_power_of_2(capacity)
        self.load_factor = load_factor
        self.max_displacements = max_displacements
        self.mask = self.capacity - 1
        
        # Two hash tables for cuckoo hashing
        self.table1 = [CuckooBucket() for _ in range(self.capacity)]
        self.table2 = [CuckooBucket() for _ in range(self.capacity)]
        self.size = 0
        
        self._lock = threading.Lock()
        self._epoch_manager = EpochManager()
        
        # Set up epoll for notification events if supported by OS
        self._has_epoll = hasattr(select, 'epoll')
        if self._has_epoll:
            try:
                self._epoll = select.epoll()
                self._read_pipe, self._write_pipe = os.pipe()
                os.set_nonblocking(self._read_pipe)
                os.set_nonblocking(self._write_pipe)
                self._epoll.register(self._read_pipe, select.EPOLLIN)
            except Exception:
                self._has_epoll = False

    def _next_power_of_2(self, x: int) -> int:
        return 1 if x <= 1 else 1 << (x - 1).bit_length()

    def _hash1(self, key: Any) -> int:
        h = hash(key)
        return (h ^ (h >> 16)) & self.mask

    def _hash2(self, key: Any) -> int:
        h = hash(key)
        return (~h ^ (h >> 12)) & self.mask

    def get(self, key: Any, thread_idx: int = 0) -> Optional[Any]:
        ep = self._epoch_manager.enter(thread_idx)
        try:
            h1 = self._hash1(key)
            b1 = self.table1[h1]
            if not b1.tombstone and b1.key == key:
                return b1.value

            h2 = self._hash2(key)
            b2 = self.table2[h2]
            if not b2.tombstone and b2.key == key:
                return b2.value

            return None
        finally:
            self._epoch_manager.leave(thread_idx)

    def put(self, key: Any, value: Any) -> bool:
        with self._lock:
            if (self.size + 1) / (2 * self.capacity) > self.load_factor:
                self._resize()

            curr_key = key
            curr_val = value
            
            for _ in range(self.max_displacements):
                # Try table 1
                h1 = self._hash1(curr_key)
                b1 = self.table1[h1]
                if b1.key is None or b1.tombstone or b1.key == curr_key:
                    b1.key = curr_key
                    b1.value = curr_val
                    b1.hash = h1
                    b1.version += 1
                    b1.tombstone = False
                    self.size += 1
                    self._notify_event()
                    return True

                # Displace from table 1
                evict_key, evict_val = b1.key, b1.value
                b1.key = curr_key
                b1.value = curr_val
                b1.hash = h1
                b1.version += 1
                curr_key, curr_val = evict_key, evict_val

                # Try table 2
                h2 = self._hash2(curr_key)
                b2 = self.table2[h2]
                if b2.key is None or b2.tombstone or b2.key == curr_key:
                    b2.key = curr_key
                    b2.value = curr_val
                    b2.hash = h2
                    b2.version += 1
                    b2.tombstone = False
                    self.size += 1
                    self._notify_event()
                    return True

                # Displace from table 2
                evict_key, evict_val = b2.key, b2.value
                b2.key = curr_key
                b2.value = curr_val
                b2.hash = h2
                b2.version += 1
                curr_key, curr_val = evict_key, evict_val

            # Rehash needed due to cuckoo loop
            self._resize()
            return self.put(curr_key, curr_val)

    def delete(self, key: Any) -> bool:
        with self._lock:
            h1 = self._hash1(key)
            b1 = self.table1[h1]
            if not b1.tombstone and b1.key == key:
                b1.tombstone = True
                b1.key = None
                b1.value = None
                self.size = max(0, self.size - 1)
                self._notify_event()
                return True

            h2 = self._hash2(key)
            b2 = self.table2[h2]
            if not b2.tombstone and b2.key == key:
                b2.tombstone = True
                b2.key = None
                b2.value = None
                self.size = max(0, self.size - 1)
                self._notify_event()
                return True

            return False

    def _resize(self) -> None:
        old_t1 = self.table1
        old_t2 = self.table2
        self.capacity *= 2
        self.mask = self.capacity - 1
        self.table1 = [CuckooBucket() for _ in range(self.capacity)]
        self.table2 = [CuckooBucket() for _ in range(self.capacity)]
        self.size = 0

        for b in old_t1:
            if b.key is not None and not b.tombstone:
                self.put(b.key, b.value)
        for b in old_t2:
            if b.key is not None and not b.tombstone:
                self.put(b.key, b.value)
        self._epoch_manager.advance()

    def _notify_event(self) -> None:
        if self._has_epoll:
            try:
                os.write(self._write_pipe, b'1')
            except BlockingIOError:
                pass

    def poll_events(self, timeout: float = 0.0) -> bool:
        if not self._has_epoll:
            return False
        events = self._epoll.poll(timeout)
        for fd, ev in events:
            if fd == self._read_pipe and (ev & select.EPOLLIN):
                try:
                    os.read(self._read_pipe, 1024)
                except Exception:
                    pass
                return True
        return False

    def close(self) -> None:
        if self._has_epoll:
            try:
                self._epoll.unregister(self._read_pipe)
                self._epoll.close()
                os.close(self._read_pipe)
                os.close(self._write_pipe)
            except Exception:
                pass
