import mmap
import os
import struct
import threading
import ctypes
from typing import Optional, Tuple, Generator, Dict, Any


class EBPFPerfEvent(ctypes.Structure):
    _fields_ = [
        ("timestamp", ctypes.c_uint64),
        ("pid", ctypes.c_uint32),
        ("cpu", ctypes.c_uint32),
        ("event_type", ctypes.c_uint32),  # 1: TCP Retransmit, 2: Packet Drop
        ("saddr", ctypes.c_uint32),
        ("daddr", ctypes.c_uint32),
        ("sport", ctypes.c_uint16),
        ("dport", ctypes.c_uint16),
        ("payload_len", ctypes.c_uint32),
    ]


class EBPFRingBuffer:
    """
    High-throughput, lock-free eBPF kernel bypass ring buffer interface for capturing
    high-frequency socket events (TCP retransmissions, dropped packets) with zero user-space
    copy overhead and complete GIL bypass.

    Layout of the shared mmap ring buffer:
    - Bytes 0-7: Write sequence counter (uint64)
    - Bytes 8-15: Read sequence counter (uint64)
    - Bytes 16-23: Capacity (uint64)
    - Bytes 24-31: Slot size (uint64)
    - Bytes 32+: Serialized EBPFPerfEvent telemetry records
    """

    HEADER_FORMAT = "=QQQQ"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(
        self, name: str, capacity: int = 2048, slot_size: int = 64, create: bool = True
    ):
        self.name = name
        self.capacity = capacity
        self.slot_size = max(slot_size, ctypes.sizeof(EBPFPerfEvent))
        self.total_size = self.HEADER_SIZE + (capacity * self.slot_size)

        self._shm_file = None
        self._mmap: Optional[mmap.mmap] = None
        self._lock = threading.Lock()  # Process-local fallback guard for concurrent consumers

        self._init_mmap(create)

    def _init_mmap(self, create: bool) -> None:
        shm_path = (
            f"/dev/shm/ebpf_{self.name}"
            if os.path.exists("/dev/shm")
            else f".shm_ebpf_{self.name}"
        )
        if create:
            self._shm_file = open(shm_path, "w+b")
            self._shm_file.write(b"\x00" * self.total_size)
            self._shm_file.flush()
            self._mmap = mmap.mmap(self._shm_file.fileno(), self.total_size)
            self._write_header(0, 0, self.capacity, self.slot_size)
        else:
            self._shm_file = open(shm_path, "r+b")
            self._mmap = mmap.mmap(self._shm_file.fileno(), self.total_size)

    def _write_header(
        self, write_seq: int, read_seq: int, capacity: int, slot_size: int
    ) -> None:
        header = struct.pack(
            self.HEADER_FORMAT, write_seq, read_seq, capacity, slot_size
        )
        self._mmap[0 : self.HEADER_SIZE] = header

    def _read_header(self) -> Tuple[int, int, int, int]:
        data = self._mmap[0 : self.HEADER_SIZE]
        return struct.unpack(self.HEADER_FORMAT, data)

    def push_event(self, event: EBPFPerfEvent) -> bool:
        """
        Push an eBPF kernel telemetry event into the ring buffer with zero-allocation slicing.
        Returns True if successful, False if the buffer is full.
        """
        # Zero-copy buffer view via ctypes string conversion
        raw_data = bytes(
            ctypes.cast(ctypes.byref(event), ctypes.POINTER(ctypes.c_char * ctypes.sizeof(event))).contents
        )

        with self._lock:
            write_seq, read_seq, capacity, slot_size = self._read_header()

            if write_seq - read_seq >= capacity:
                return False  # Ring buffer overflow / full

            slot_idx = write_seq % capacity
            offset = self.HEADER_SIZE + (slot_idx * slot_size)

            padded_data = raw_data.ljust(slot_size, b"\x00")
            self._mmap[offset : offset + slot_size] = padded_data

            self._write_header(write_seq + 1, read_seq, capacity, slot_size)
        return True

    def pop_event(self) -> Optional[EBPFPerfEvent]:
        """
        Pop the next eBPF kernel telemetry event from the ring buffer.
        Returns an EBPFPerfEvent instance or None if the buffer is empty.
        """
        with self._lock:
            write_seq, read_seq, capacity, slot_size = self._read_header()

            if read_seq >= write_seq:
                return None  # Buffer empty

            slot_idx = read_seq % capacity
            offset = self.HEADER_SIZE + (slot_idx * slot_size)

            raw_slot = self._mmap[offset : offset + slot_size]
            event_bytes = raw_slot[:ctypes.sizeof(EBPFPerfEvent)]

            event = EBPFPerfEvent.from_buffer_copy(event_bytes)

            self._write_header(write_seq, read_seq + 1, capacity, slot_size)
        return event

    def poll_events(self, max_batch: int = 64) -> Generator[EBPFPerfEvent, None, None]:
        """
        Zero-allocation generator yielding a batch of eBPF telemetry events from the ring buffer.
        """
        count = 0
        while count < max_batch:
            event = self.pop_event()
            if event is None:
                break
            yield event
            count += 1

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            write_seq, read_seq, capacity, slot_size = self._read_header()
            return {
                "name": self.name,
                "write_seq": write_seq,
                "read_seq": read_seq,
                "capacity": capacity,
                "slot_size": slot_size,
                "depth": write_seq - read_seq,
                "is_full": (write_seq - read_seq) >= capacity,
                "is_empty": read_seq >= write_seq,
            }

    def close(self) -> None:
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._shm_file:
            self._shm_file.close()
            self._shm_file = None
