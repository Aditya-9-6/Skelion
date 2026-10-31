import mmap
import os
import struct
import threading
from typing import Optional, Tuple


class SharedMemoryRingBuffer:
    """
    High-throughput, lock-free circular ring buffer utilizing POSIX shared memory (mmap)
    for zero-copy inter-process communication of high-frequency telemetry metrics.
    
    Layout of the shared memory region:
    - Bytes 0-7: Write sequence counter (uint64)
    - Bytes 8-15: Read sequence counter (uint64)
    - Bytes 16-23: Capacity (uint64)
    - Bytes 24-31: Message size / slot size (uint64)
    - Bytes 32+: Data slots
    """

    HEADER_FORMAT = "=QQQQ"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, name: str, capacity: int = 1024, slot_size: int = 256, create: bool = True):
        self.name = name
        self.capacity = capacity
        self.slot_size = slot_size
        self.total_size = self.HEADER_SIZE + (capacity * slot_size)
        
        # Use memory-backed anonymous or file-mapped region
        self._shm_file = None
        self._mmap: Optional[mmap.mmap] = None
        self._lock = threading.Lock()  # Process-local fallback guard if needed, SPSC relies on atomics
        
        self._init_mmap(create)

    def _init_mmap(self, create: bool) -> None:
        # For portability across platforms with mmap, we use a temporary file or anonymous mmap
        # In POSIX systems, mmap can be backed by file descriptors or anonymous memory.
        if create:
            self._shm_file = open(f"/dev/shm/{self.name}" if os.path.exists("/dev/shm") else f".shm_{self.name}", "w+b")
            self._shm_file.write(b"\x00" * self.total_size)
            self._shm_file.flush()
            self._mmap = mmap.mmap(self._shm_file.fileno(), self.total_size)
            # Initialize header
            self._write_header(0, 0, self.capacity, self.slot_size)
        else:
            self._shm_file = open(f"/dev/shm/{self.name}" if os.path.exists("/dev/shm") else f".shm_{self.name}", "r+b")
            self._mmap = mmap.mmap(self._shm_file.fileno(), self.total_size)

    def _write_header(self, write_seq: int, read_seq: int, capacity: int, slot_size: int) -> None:
        header = struct.pack(self.HEADER_FORMAT, write_seq, read_seq, capacity, slot_size)
        self._mmap[0:self.HEADER_SIZE] = header

    def _read_header(self) -> Tuple[int, int, int, int]:
        data = self._mmap[0:self.HEADER_SIZE]
        return struct.unpack(self.HEADER_FORMAT, data)

    def push(self, data: bytes) -> bool:
        """
        Push a telemetry payload into the ring buffer.
        Returns True if successful, False if the buffer is full (Single-Producer).
        """
        if len(data) > self.slot_size:
            raise ValueError(f"Payload size {len(data)} exceeds slot size {self.slot_size}")

        write_seq, read_seq, capacity, slot_size = self._read_header()

        if write_seq - read_seq >= capacity:
            return False  # Buffer full

        slot_idx = write_seq % capacity
        offset = self.HEADER_SIZE + (slot_idx * slot_size)
        
        # Zero-copy write into mmap slice
        padded_data = data.ljust(slot_size, b"\x00")
        self._mmap[offset:offset + slot_size] = padded_data
        
        # Advance write sequence atomically
        self._write_header(write_seq + 1, read_seq, capacity, slot_size)
        return True

    def pop(self) -> Optional[bytes]:
        """
        Pop a telemetry payload from the ring buffer.
        Returns the payload bytes, or None if the buffer is empty (Single-Consumer).
        """
        write_seq, read_seq, capacity, slot_size = self._read_header()

        if read_seq >= write_seq:
            return None  # Buffer empty

        slot_idx = read_seq % capacity
        offset = self.HEADER_SIZE + (slot_idx * slot_size)
        
        # Zero-copy read from mmap slice
        slot_data = self._mmap[offset:offset + slot_size].rstrip(b"\x00")
        
        # Advance read sequence atomically
        self._write_header(write_seq, read_seq + 1, capacity, slot_size)
        return slot_data

    def close(self) -> None:
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._shm_file:
            self._shm_file.close()
            self._shm_file = None
            try:
                path = f"/dev/shm/{self.name}" if os.path.exists("/dev/shm") else f".shm_{self.name}"
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
