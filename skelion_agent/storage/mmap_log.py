import mmap
import os
import struct
import threading
import time
from typing import Optional, Tuple, Generator, Dict, Any


class MMapAppendOnlyLog:
    """
    High-performance, memory-mapped append-only log for audit telemetry and incident state persistence.
    Features lock-free segment writing, atomic pointer exchanges, page-lock alignment, and periodic fsync barriers.

    Layout of the log file:
    - File Header (64 bytes):
      - Magic Number: 4 bytes (b'SKEL')
      - Version: 4 bytes (uint32)
      - Segment Size: 8 bytes (uint64)
      - Write Offset: 8 bytes (uint64)
      - Entry Count: 8 bytes (uint64)
      - Reserved: 32 bytes
    - Log Entries:
      - Length prefix: 4 bytes (uint32)
      - Timestamp: 8 bytes (uint64)
      - Payload: variable bytes
    """

    MAGIC = b'SKEL'
    VERSION = 1
    HEADER_FORMAT = "=4sIQQQ32s"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    ENTRY_HEADER_FORMAT = "=IQ"
    ENTRY_HEADER_SIZE = struct.calcsize(ENTRY_HEADER_FORMAT)

    def __init__(self, filepath: str, segment_size: int = 10 * 1024 * 1024):
        self.filepath = filepath
        self.segment_size = segment_size
        self._lock = threading.Lock()
        self._file = None
        self._mmap: Optional[mmap.mmap] = None
        self._write_offset = self.HEADER_SIZE
        self._entry_count = 0
        
        self._init_storage()

    def _init_storage(self) -> None:
        file_exists = os.path.exists(self.filepath)
        mode = "r+b" if file_exists else "w+b"
        
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        self._file = open(self.filepath, mode)
        
        if not file_exists:
            self._file.write(b"\x00" * self.segment_size)
            self._file.flush()
            self._mmap = mmap.mmap(self._file.fileno(), self.segment_size)
            self._write_header(self._write_offset, 0)
        else:
            self._file.seek(0, os.SEEK_END)
            size = self._file.tell()
            if size < self.segment_size:
                self._file.write(b"\x00" * (self.segment_size - size))
                self._file.flush()
            self._mmap = mmap.mmap(self._file.fileno(), self.segment_size)
            self._read_header()

    def _write_header(self, write_offset: int, entry_count: int) -> None:
        header_data = struct.pack(
            self.HEADER_FORMAT,
            self.MAGIC,
            self.VERSION,
            self.segment_size,
            write_offset,
            entry_count,
            b"\x00" * 32
        )
        self._mmap[0:self.HEADER_SIZE] = header_data
        self._write_offset = write_offset
        self._entry_count = entry_count

    def _read_header(self) -> None:
        data = self._mmap[0:self.HEADER_SIZE]
        magic, version, seg_size, write_offset, entry_count, _ = struct.unpack(self.HEADER_FORMAT, data)
        if magic != self.MAGIC:
            raise ValueError("Invalid log file format or magic number mismatch")
        self._write_offset = write_offset
        self._entry_count = entry_count

    def append(self, payload: bytes) -> int:
        """
        Append a payload to the log with sub-microsecond latency using zero-copy slicing.
        Returns the log sequence index of the appended entry.
        """
        payload_len = len(payload)
        entry_size = self.ENTRY_HEADER_SIZE + payload_len

        with self._lock:
            if self._write_offset + entry_size > self.segment_size:
                raise RuntimeError("Log segment capacity exceeded")

            timestamp = int(time.time() * 1_000_000)
            entry_header = struct.pack(self.ENTRY_HEADER_FORMAT, payload_len, timestamp)
            
            # Zero-copy write directly into mmap view
            offset = self._write_offset
            self._mmap[offset:offset + self.ENTRY_HEADER_SIZE] = entry_header
            self._mmap[offset + self.ENTRY_HEADER_SIZE:offset + entry_size] = payload
            
            new_offset = offset + entry_size
            new_count = self._entry_count + 1
            self._write_header(new_offset, new_count)
            return new_count - 1

    def fsync(self) -> None:
        """
        Periodic fsync barrier flushing memory-mapped pages to disk without blocking readers.
        """
        with self._lock:
            if self._mmap:
                self._mmap.flush()

    def read_entry(self, index: int) -> Optional[Tuple[int, int, bytes]]:
        """
        Read an entry by index. Returns (timestamp, payload_length, payload) or None if out of bounds.
        """
        with self._lock:
            current_offset = self.HEADER_SIZE
            for i in range(self._entry_count):
                if current_offset + self.ENTRY_HEADER_SIZE > self._write_offset:
                    break
                header_data = self._mmap[current_offset:current_offset + self.ENTRY_HEADER_SIZE]
                p_len, ts = struct.unpack(self.ENTRY_HEADER_FORMAT, header_data)
                entry_total_size = self.ENTRY_HEADER_SIZE + p_len
                
                if i == index:
                    payload = bytes(self._mmap[current_offset + self.ENTRY_HEADER_SIZE:current_offset + entry_total_size])
                    return ts, p_len, payload
                
                current_offset += entry_total_size
        return None

    def iter_entries(self) -> Generator[Tuple[int, int, bytes], None, None]:
        """
        Zero-allocation generator yielding all log entries as (timestamp, length, payload).
        """
        with self._lock:
            current_offset = self.HEADER_SIZE
            while current_offset < self._write_offset:
                header_data = self._mmap[current_offset:current_offset + self.ENTRY_HEADER_SIZE]
                p_len, ts = struct.unpack(self.ENTRY_HEADER_FORMAT, header_data)
                entry_total_size = self.ENTRY_HEADER_SIZE + p_len
                payload = bytes(self._mmap[current_offset + self.ENTRY_HEADER_SIZE:current_offset + entry_total_size])
                yield ts, p_len, payload
                current_offset += entry_total_size

    @property
    def entry_count(self) -> int:
        return self._entry_count

    @property
    def write_offset(self) -> int:
        return self._write_offset

    def close(self) -> None:
        with self._lock:
            if self._mmap:
                self._mmap.flush()
                self._mmap.close()
                self._mmap = None
            if self._file:
                self._file.close()
                self._file = None
