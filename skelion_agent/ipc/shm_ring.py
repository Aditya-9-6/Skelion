import mmap
import struct
import threading
from typing import Optional, Tuple
from multiprocessing import shared_memory


class SharedMemoryRingBuffer:
    """
    High-throughput, lock-free circular ring buffer utilizing Python's multiprocessing.shared_memory
    and mmap for zero-copy inter-process and intra-process communication of high-frequency telemetry metrics
    and autonomous agent state updates.

    Layout of the shared memory region:
    - Bytes 0-7: Write sequence counter (uint64)
    - Bytes 8-15: Read sequence counter (uint64)
    - Bytes 16-23: Capacity (uint64)
    - Bytes 24-31: Message size / slot size (uint64)
    - Bytes 32+: Data slots
    """

    HEADER_FORMAT = "=QQQQ"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(
        self, name: str, capacity: int = 1024, slot_size: int = 256, create: bool = True
    ):
        self.name = name
        self.capacity = capacity
        self.slot_size = slot_size
        self.total_size = self.HEADER_SIZE + (capacity * slot_size)

        self._shm: Optional[shared_memory.SharedMemory] = None
        self._mmap: Optional[mmap.mmap] = None
        self._lock = threading.Lock()

        self._init_shm(create)

    def _init_shm(self, create: bool) -> None:
        shm_name = f"skelion_shm_ring_{self.name}"
        if create:
            try:
                existing = shared_memory.SharedMemory(name=shm_name, create=False)
                existing.close()
                existing.unlink()
            except Exception:
                pass
            self._shm = shared_memory.SharedMemory(
                name=shm_name, create=True, size=self.total_size
            )
            self._mmap = self._shm.buf
            self._write_header(0, 0, self.capacity, self.slot_size)
        else:
            self._shm = shared_memory.SharedMemory(name=shm_name, create=False)
            self._mmap = self._shm.buf

    def _write_header(
        self, write_seq: int, read_seq: int, capacity: int, slot_size: int
    ) -> None:
        struct.pack_into(
            self.HEADER_FORMAT, self._mmap, 0, write_seq, read_seq, capacity, slot_size
        )

    def _read_header(self) -> Tuple[int, int, int, int]:
        return struct.unpack_from(self.HEADER_FORMAT, self._mmap, 0)

    def push(self, data: bytes) -> bool:
        """
        Push a telemetry payload into the ring buffer without allocations on hot paths.
        Returns True if successful, False if the buffer is full.
        """
        if len(data) > self.slot_size:
            raise ValueError(
                f"Payload size {len(data)} exceeds slot size {self.slot_size}"
            )

        with self._lock:
            write_seq, read_seq, capacity, slot_size = self._read_header()

            if (write_seq - read_seq) >= capacity:
                return False

            slot_idx = write_seq % capacity
            offset = self.HEADER_SIZE + (slot_idx * slot_size)

            view = self._mmap[offset : offset + slot_size]
            view[: len(data)] = data
            if len(data) < slot_size:
                view[len(data) :] = b"\x00" * (slot_size - len(data))

            self._write_header(write_seq + 1, read_seq, capacity, slot_size)
            return True

    def pop(self) -> Optional[bytes]:
        """
        Pop a telemetry payload from the ring buffer.
        Returns the payload bytes, or None if the buffer is empty.
        """
        with self._lock:
            write_seq, read_seq, capacity, slot_size = self._read_header()

            if read_seq >= write_seq:
                return None

            slot_idx = read_seq % capacity
            offset = self.HEADER_SIZE + (slot_idx * slot_size)

            view = self._mmap[offset : offset + slot_size]
            # Find null termination or take full slot
            null_idx = view.find(b"\x00")
            payload = bytes(view[: null_idx if null_idx != -1 else slot_size])

            self._write_header(write_seq, read_seq + 1, capacity, slot_size)
            return payload

    def close(self) -> None:
        try:
            if self._shm:
                self._shm.close()
        except Exception:
            pass

    def unlink(self) -> None:
        try:
            if self._shm:
                self._shm.unlink()
        except Exception:
            pass
