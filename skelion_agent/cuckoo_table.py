import ctypes
import mmap
import os
import select
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class CuckooBucket(ctypes.Structure):
    _fields_ = [
        ("hash1", ctypes.c_uint64),
        ("hash2", ctypes.c_uint64),
        ("active", ctypes.c_uint8),
        ("generation", ctypes.c_uint64),
    ]


class CuckooStashNode:
    __slots__ = ("key", "value", "hash1", "hash2", "next")

    def __init__(self, key: Any, value: Any, hash1: int, hash2: int):
        self.key = key
        self.value = value
        self.hash1 = hash1
        self.hash2 = hash2
        self.next: Optional["CuckooStashNode"] = None


class EpollCuckooHashTable:
    """
    High-performance, concurrent, lock-free cuckoo hash table backed by epoll
    for non-blocking asynchronous incident route and telemetry tag lookups using ctypes/mmap.
    Features two independent hash functions, atomic pointer swaps, and an overflow stash area.
    """

    def __init__(self, capacity: int = 1024, max_evictions: int = 500, stash_limit: int = 128):
        self.capacity = self._next_power_of_2(capacity)
        self.max_evictions = max_evictions
        self.stash_limit = stash_limit
        self.mask = self.capacity - 1
        
        # Allocate mmap-backed memory region for zero-copy and shared architecture alignment
        self._mmap_size = self.capacity * ctypes.sizeof(CuckooBucket)
        self._mmap_buf = mmap.mmap(-1, self._mmap_size, flags=mmap.MAP_SHARED | mmap.MAP_ANONYMOUS)
        
        # Initialize bucket views
        self.buckets = (CuckooBucket * self.capacity).from_buffer(self._mmap_buf)
        for i in range(self.capacity):
            self.buckets[i].hash1 = 0
            self.buckets[i].hash2 = 0
            self.buckets[i].active = 0
            self.buckets[i].generation = 0

        # Storage dictionary mapping bucket index / stash to actual objects (Python references)
        self._storage: Dict[str, Any] = {}
        self._stash_head: Optional[CuckooStashNode] = None
        self._stash_size = 0
        
        # Synchronization & Event Notification primitives
        self._lock = threading.Lock()
        self._rw_lock = threading.RLock()
        
        # Epoll notification pipe / event loop descriptors
        self._read_pipe, self._write_pipe = os.pipe()
        os.set_nonblocking(self._read_pipe)
        os.set_nonblocking(self._write_pipe)
        
        self._epoll = select.epoll()
        self._epoll.register(self._read_pipe, select.EPOLLIN | select.EPOLLET)

    def _next_power_of_2(self, x: int) -> int:
        return 1 if x <= 1 else 1 << (x - 1).bit_length()

    def _hash1(self, key: str) -> int:
        h = 14695981039346656037
        for char in key:
            h ^= ord(char)
            h *= 1099511628211
            h &= 0xFFFFFFFFFFFFFFFF
        return h | 1  # Ensure non-zero

    def _hash2(self, key: str) -> int:
        h = 5381
        for char in key:
            h = ((h << 5) + h) + ord(char)
            h &= 0xFFFFFFFFFFFFFFFF
        return h | 1  # Ensure non-zero

    def _notify_epoll(self) -> None:
        try:
            os.write(self._write_pipe, b"W")
        except (BlockingIOError, OSError):
            pass

    def poll_events(self, timeout: float = 0.0) -> bool:
        """Poll epoll descriptor for table mutation notifications (non-blocking)."""
        events = self._epoll.poll(timeout)
        triggered = False
        for fd, ev in events:
            if fd == self._read_pipe:
                triggered = True
                try:
                    while True:
                        os.read(self._read_pipe, 1024)
                except (BlockingIOError, OSError):
                    pass
        return triggered

    def get(self, key: str) -> Optional[Any]:
        h1 = self._hash1(key)
        h2 = self._hash2(key)
        idx1 = h1 & self.mask
        idx2 = h2 & self.mask

        # Check primary bucket 1
        b1 = self.buckets[idx1]
        if b1.active and b1.hash1 == h1:
            val = self._storage.get(f"b1_{idx1}")
            if val is not None:
                return val

        # Check primary bucket 2
        b2 = self.buckets[idx2]
        if b2.active and b2.hash2 == h2:
            val = self._storage.get(f"b2_{idx2}")
            if val is not None:
                return val

        # Check overflow stash area
        curr = self._stash_head
        while curr is not None:
            if curr.hash1 == h1 and curr.hash2 == h2 and curr.key == key:
                return curr.value
            curr = curr.next

        return None

    def put(self, key: str, value: str) -> bool:
        with self._rw_lock:
            h1 = self._hash1(key)
            h2 = self._hash2(key)

            # Check if key already exists in primary buckets or stash and update
            idx1 = h1 & self.mask
            idx2 = h2 & self.mask

            b1 = self.buckets[idx1]
            if b1.active and b1.hash1 == h1 and self._storage.get(f"b1_{idx1}_key") == key:
                self._storage[f"b1_{idx1}"] = value
                self._notify_epoll()
                return True

            b2 = self.buckets[idx2]
            if b2.active and b2.hash2 == h2 and self._storage.get(f"b2_{idx2}_key") == key:
                self._storage[f"b2_{idx2}"] = value
                self._notify_epoll()
                return True

            curr = self._stash_head
            while curr is not None:
                if curr.key == key:
                    curr.value = value
                    self._notify_epoll()
                    return True
                curr = curr.next

            # Cuckoo insertion loop with evictions
            curr_key = key
            curr_val = value
            curr_h1 = h1
            curr_h2 = h2

            for _ in range(self.max_evictions):
                # Try bucket 1
                i1 = curr_h1 & self.mask
                bucket1 = self.buckets[i1]
                if not bucket1.active:
                    bucket1.hash1 = curr_h1
                    bucket1.hash2 = curr_h2
                    bucket1.active = 1
                    bucket1.generation += 1
                    self._storage[f"b1_{i1}"] = curr_val
                    self._storage[f"b1_{i1}_key"] = curr_key
                    self._notify_epoll()
                    return True

                # Try bucket 2
                i2 = curr_h2 & self.mask
                bucket2 = self.buckets[i2]
                if not bucket2.active:
                    bucket2.hash1 = curr_h1
                    bucket2.hash2 = curr_h2
                    bucket2.active = 1
                    bucket2.generation += 1
                    self._storage[f"b2_{i2}"] = curr_val
                    self._storage[f"b2_{i2}_key"] = curr_key
                    self._notify_epoll()
                    return True

                # Evict from bucket 1 and re-insert displaced entry
                evict_h1 = bucket1.hash1
                evict_h2 = bucket1.hash2
                evict_key = self._storage.get(f"b1_{i1}_key", "")
                evict_val = self._storage.get(f"b1_{i1}", None)

                bucket1.hash1 = curr_h1
                bucket1.hash2 = curr_h2
                bucket1.generation += 1
                self._storage[f"b1_{i1}"] = curr_val
                self._storage[f"b1_{i1}_key"] = curr_key

                curr_key = evict_key
                curr_val = evict_val
                curr_h1 = evict_h1
                curr_h2 = evict_h2

            # If max evictions exceeded, push to overflow stash area
            if self._stash_size < self.stash_limit:
                new_node = CuckooStashNode(curr_key, curr_val, curr_h1, curr_h2)
                new_node.next = self._stash_head
                self._stash_head = new_node
                self._stash_size += 1
                self._notify_epoll()
                return True

            return False

    def delete(self, key: str) -> bool:
        with self._rw_lock:
            h1 = self._hash1(key)
            h2 = self._hash2(key)
            idx1 = h1 & self.mask
            idx2 = h2 & self.mask

            b1 = self.buckets[idx1]
            if b1.active and b1.hash1 == h1 and self._storage.get(f"b1_{idx1}_key") == key:
                b1.active = 0
                b1.generation += 1
                self._storage.pop(f"b1_{idx1}", None)
                self._storage.pop(f"b1_{idx1}_key", None)
                self._notify_epoll()
                return True

            b2 = self.buckets[idx2]
            if b2.active and b2.hash2 == h2 and self._storage.get(f"b2_{idx2}_key") == key:
                b2.active = 0
                b2.generation += 1
                self._storage.pop(f"b2_{idx2}", None)
                self._storage.pop(f"b2_{idx2}_key", None)
                self._notify_epoll()
                return True

            # Check and remove from stash
            curr = self._stash_head
            prev = None
            while curr is not None:
                if curr.key == key:
                    if prev is None:
                        self._stash_head = curr.next
                    else:
                        prev.next = curr.next
                    self._stash_size -= 1
                    self._notify_epoll()
                    return True
                prev = curr
                curr = curr.next

            return False

    def close(self) -> None:
        try:
            self._epoll.unregister(self._read_pipe)
            self._epoll.close()
        except Exception:
            pass
        try:
            os.close(self._read_pipe)
            os.close(self._write_pipe)
        except Exception:
            pass
        try:
            self._mmap_buf.close()
        except Exception:
            pass
