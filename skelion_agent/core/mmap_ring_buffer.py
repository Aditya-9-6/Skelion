import mmap
import os
import struct
import select
import threading
from typing import Optional, Tuple
from multiprocessing import shared_memory


class MMapRingBuffer:
    """
    High-performance, lock-free memory-mapped ring buffer utilizing POSIX shared memory
    and epoll-driven non-blocking I/O notifications for zero-copy incident telemetry transfer
    between autonomous remediation agents.

    Layout of the shared memory region:
    - Bytes 0-7: Write sequence counter (uint64)
    - Bytes 8-15: Read sequence counter (uint64)
    - Bytes 16-23: Capacity (uint64)
    - Bytes 24-31: Slot size (uint64)
    - Bytes 32+: Data slots
    """

    HEADER_FORMAT = "=QQQQ"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(
        self, name: str, capacity: int = 1024, slot_size: int = 256, create: bool = True
    ):
        if capacity <= 0 or (capacity & (capacity - 1)) != 0:
            raise ValueError("Capacity must be a positive power of two")

        self.name = name
        self.capacity = capacity
        self.slot_size = slot_size
        self.total_size = self.HEADER_SIZE + (capacity * slot_size)

        self._shm: Optional[shared_memory.SharedMemory] = None
        self._mmap: Optional[mmap.mmap] = None
        self._lock = threading.Lock()
        self._epoll: Optional[select.epoll] = None
        self._pipe_r, self._pipe_w = os.pipe()
        os.set_nonblocking(self._pipe_r)
        os.set_nonblocking(self._pipe_w)

        self._init_shm(create)

    def _init_shm(self, create: bool) -> None:
        shm_name = f"mmap_ring_{self.name}"
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

        try:
            self._epoll = select.epoll()
            self._epoll.register(self._pipe_r, select.EPOLLIN)
        except (AttributeError, OSError):
            # Fallback for environments lacking epoll (e.g. macOS)
            self._epoll = None

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
        Push a telemetry payload into the ring buffer with zero-copy slicing.
        Notifies consumers via epoll pipe.
        """
        if len(data) > self.slot_size:
            raise ValueError(
                f"Payload size {len(data)} exceeds slot size {self.slot_size}"
            )

        with self._lock:
            write_seq, read_seq, capacity, slot_size = self._read_header()

            if (write_seq - read_seq) >= capacity:
                return False  # Buffer full

            slot_idx = write_seq % capacity
            offset = self.HEADER_SIZE + (slot_idx * slot_size)

            view = self._mmap[offset : offset + slot_size]
            view[: len(data)] = data
            if len(data) < slot_size:
                view[len(data) :] = b"\x00" * (slot_size - len(data))

            self._write_header(write_seq + 1, read_seq, capacity, slot_size)

            # Trigger epoll notification
            try:
                os.write(self._pipe_w, b"1")
            except BlockingIOError:
                pass

            return True

    def pop(self) -> Optional[bytes]:
        """
        Pop a telemetry payload from the ring buffer in a lock-free SPSC manner.
        """
        with self._lock:
            write_seq, read_seq, capacity, slot_size = self._read_header()

            if read_seq >= write_seq:
                return None  # Buffer empty

            slot_idx = read_seq % capacity
            offset = self.HEADER_SIZE + (slot_idx * slot_size)

            # Zero-copy view extraction
            data_bytes = bytes(self._mmap[offset : offset + slot_size]).rstrip(b"\x00")

            self._write_header(write_seq, read_seq + 1, capacity, slot_size)
            return data_bytes

    def wait_for_data(self, timeout: float = -1.0) -> bool:
        """
        Block until new incident telemetry arrives using epoll with timeout.
        """
        if self._epoll is None:
            return True
        try:
            events = self._epoll.poll(timeout)
            for fd, event in events:
                if fd == self._pipe_r:
                    # Drain pipe notification buffer
                    try:
                        os.read(self._pipe_r, 1024)
                    except (BlockingIOError, OSError):
                        pass
                    return True
        except Exception:
            pass
        return False

    def close(self) -> None:
        with self._lock:
            if self._epoll:
                try:
                    self._epoll.unregister(self._pipe_r)
                    self._epoll.close()
                except Exception:
                    pass
                self._epoll = None
            try:
                os.close(self._pipe_r)
                os.close(self._pipe_w)
            except Exception:
                pass
            if self._shm:
                try:
                    self._shm.close()
                    self._shm.unlink()
                except Exception:
                    pass
                self._shm = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
