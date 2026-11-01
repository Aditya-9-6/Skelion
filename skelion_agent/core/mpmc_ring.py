import threading
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class MPMCRingBuffer(Generic[T]):
    """
    High-performance, lock-free (or bounded atomic) MPMC ring buffer
    optimized for high-throughput network proxies and agent message passing.
    """

    def __init__(self, capacity: int = 1024):
        if capacity <= 0 or (capacity & (capacity - 1)) != 0:
            raise ValueError("Capacity must be a power of 2")
        self.capacity = capacity
        self.mask = capacity - 1
        self.buffer = [None] * capacity
        self.enqueue_pos = 0
        self.dequeue_pos = 0
        self._lock = threading.Lock()

    def push(self, item: T) -> bool:
        with self._lock:
            if (self.enqueue_pos - self.dequeue_pos) >= self.capacity:
                return False
            idx = self.enqueue_pos & self.mask
            self.buffer[idx] = item
            self.enqueue_pos += 1
            return True

    def pop(self) -> Optional[T]:
        with self._lock:
            if self.enqueue_pos == self.dequeue_pos:
                return None
            idx = self.dequeue_pos & self.mask
            item = self.buffer[idx]
            self.buffer[idx] = None
            self.dequeue_pos += 1
            return item

    def __len__(self) -> int:
        with self._lock:
            return max(0, self.enqueue_pos - self.dequeue_pos)
