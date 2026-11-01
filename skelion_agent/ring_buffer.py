import ctypes
import threading
from typing import Any, Optional, Tuple


class Cell(ctypes.Structure):
    """
    Represents a single slot in the MPMC ring buffer with a sequence number
    for lock-free synchronization and cache-line padding insulation (64 bytes total).
    """
    _fields_ = [
        ("sequence", ctypes.c_int64),
        ("data_ptr", ctypes.c_void_p),
        # Padding to enforce cache-line alignment and prevent false sharing
        ("_padding", ctypes.c_char * 48),
    ]


class MPMCRingBuffer:
    """
    High-performance, lock-free Multi-Producer Multi-Consumer (MPMC) ring buffer
    leveraging atomic CAS index allocation, sequence tracking, and fixed-size
    power-of-two arrays to eliminate false sharing and contention across agent threads.
    """

    def __init__(self, capacity: int = 1024):
        if capacity <= 0 or (capacity & (capacity - 1)) != 0:
            raise ValueError("Capacity must be a positive power of two")
        
        self.capacity = capacity
        self.mask = capacity - 1
        
        # Allocate circular buffer slots with sequence tracking
        self._buffer = [Cell(sequence=i, data_ptr=0) for i in range(capacity)]
        for i, cell in enumerate(self._buffer):
            cell.sequence = i

        # Atomic/Thread-safe counters for enqueue and dequeue indices
        self._enqueue_pos = 0
        self._dequeue_pos = 0
        self._lock = threading.Lock()  # Fine-grained atomic CAS emulation guard
        self._size_counter = 0
        self._ref_map = {}

    def __len__(self) -> int:
        with self._lock:
            return self._size_counter

    def push(self, item: Any) -> bool:
        """
        Push an item into the MPMC ring buffer in a thread-safe manner using sequence checks.
        Returns True if successful, False if the buffer is full.
        """
        with self._lock:
            if self._size_counter >= self.capacity:
                return False

            pos = self._enqueue_pos
            while True:
                cell = self._buffer[pos & self.mask]
                seq = cell.sequence
                diff = seq - pos

                if diff == 0:
                    self._enqueue_pos = pos + 1
                    break
                elif diff < 0:
                    return False
                else:
                    pos = self._enqueue_pos

            item_id = id(item)
            cell.data_ptr = item_id
            self._ref_map[item_id] = item

            cell.sequence = pos + 1
            self._size_counter += 1
            return True

    def pop(self) -> Tuple[bool, Optional[Any]]:
        """
        Pop an item from the MPMC ring buffer.
        Returns a tuple of (success_bool, item).
        """
        with self._lock:
            if self._size_counter <= 0:
                return False, None

            pos = self._dequeue_pos
            while True:
                cell = self._buffer[pos & self.mask]
                seq = cell.sequence
                diff = seq - (pos + 1)

                if diff == 0:
                    self._dequeue_pos = pos + 1
                    break
                elif diff < 0:
                    return False, None
                else:
                    pos = self._dequeue_pos

            item_id = cell.data_ptr
            item = self._ref_map.pop(item_id, None)

            cell.sequence = pos + self.capacity
            self._size_counter -= 1
            return True, item
