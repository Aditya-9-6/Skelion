import ctypes
import ctypes.util
import errno
import logging
import os
import socket
import threading
import time
from typing import Callable, Dict

logger = logging.getLogger(__name__)

# Load C library for epoll syscalls on Linux
_libc_name = ctypes.util.find_library("c")
_libc = ctypes.CDLL(_libc_name, use_errno=True) if _libc_name else None

# Constants for epoll
EPOLLIN = 0x001
EPOLLOUT = 0x004
EPOLLERR = 0x008
EPOLLHUP = 0x010
EPOLLET = 1 << 31

EPOLL_CTL_ADD = 1
EPOLL_CTL_MOD = 2
EPOLL_CTL_DEL = 3


# Define epoll_event layout
class EpollEventStruct(ctypes.Structure):
    _fields_ = [
        ("events", ctypes.c_uint32),
        ("data", ctypes.c_uint64),
    ]


class ZeroCopyReactor:
    """
    High-throughput, edge-triggered epoll reactor using ctypes to wrap low-level system calls
    for asynchronous incident telemetry ingestion and zero-copy page buffer management.
    """

    def __init__(self, max_events: int = 1024, page_size: int = 4096):
        self.max_events = max_events
        self.page_size = page_size
        self._epoll_fd = -1
        self._running = False
        self._lock = threading.Lock()
        self._callbacks: Dict[int, Callable[[int, bytes], None]] = {}
        self._socket_map: Dict[int, socket.socket] = {}
        self._buffers: Dict[int, memoryview] = {}

        if _libc:
            try:
                self._epoll_fd = _libc.epoll_create1(0)
                if self._epoll_fd < 0:
                    errno_val = ctypes.get_errno()
                    raise OSError(errno_val, os.strerror(errno_val))
            except Exception as e:
                logger.warning(
                    f"Failed to create epoll instance via ctypes: {e}. Falling back to mock/simulation mode."
                )
                self._epoll_fd = -1

    def register_socket(
        self, sock: socket.socket, callback: Callable[[int, bytes], None]
    ) -> None:
        """Register a non-blocking socket descriptor with edge-triggered epoll."""
        sock.setblocking(False)
        fd = sock.fileno()

        with self._lock:
            self._socket_map[fd] = sock
            self._callbacks[fd] = callback
            # Pre-allocate memory-mapped page buffer for zero-copy ingestion
            raw_buf = bytearray(self.page_size)
            self._buffers[fd] = memoryview(raw_buf)

            if self._epoll_fd >= 0 and _libc:
                ev = EpollEventStruct()
                ev.events = EPOLLIN | EPOLLET | EPOLLERR | EPOLLHUP
                ev.data = fd
                res = _libc.epoll_ctl(
                    self._epoll_fd, EPOLL_CTL_ADD, fd, ctypes.byref(ev)
                )
                if res < 0:
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))

    def unregister_socket(self, sock: socket.socket) -> None:
        """Unregister a socket descriptor from the reactor."""
        try:
            fd = sock.fileno()
        except Exception:
            return

        with self._lock:
            if self._epoll_fd >= 0 and _libc:
                _libc.epoll_ctl(self._epoll_fd, EPOLL_CTL_DEL, fd, None)
            self._socket_map.pop(fd, None)
            self._callbacks.pop(fd, None)
            self._buffers.pop(fd, None)

    def poll_once(self, timeout_ms: int = 100) -> int:
        """Poll the epoll descriptor once and dispatch events."""
        if self._epoll_fd < 0 or not _libc:
            time.sleep(timeout_ms / 1000.0)
            return 0

        events_array = (EpollEventStruct * self.max_events)()
        nevents = _libc.epoll_wait(
            self._epoll_fd, events_array, self.max_events, timeout_ms
        )

        if nevents < 0:
            err = ctypes.get_errno()
            if err == errno.EINTR:
                return 0
            raise OSError(err, os.strerror(err))

        for i in range(nevents):
            ev = events_array[i]
            fd = int(ev.data)
            events = int(ev.events)

            with self._lock:
                callback = self._callbacks.get(fd)
                sock = self._socket_map.get(fd)
                buf = self._buffers.get(fd)

            if not callback or not sock:
                continue

            if events & (EPOLLERR | EPOLLHUP):
                try:
                    callback(fd, b"")
                finally:
                    self.unregister_socket(sock)
                continue

            if events & EPOLLIN:
                try:
                    # Zero-copy read directly into pre-allocated memoryview buffer
                    while True:
                        try:
                            # Read into the underlying buffer slice via socket recvinto
                            nbytes = sock.recv_into(buf)
                            if nbytes == 0:
                                # Connection closed
                                callback(fd, b"")
                                self.unregister_socket(sock)
                                break
                            else:
                                callback(fd, bytes(buf[:nbytes]))
                        except BlockingIOError:
                            break
                        except (ConnectionResetError, BrokenPipeError):
                            callback(fd, b"")
                            self.unregister_socket(sock)
                            break
                except Exception as e:
                    logger.error(f"Error processing read on fd {fd}: {e}")
                    self.unregister_socket(sock)

        return nevents

    def close(self) -> None:
        """Close the epoll descriptor and clean up all sockets."""
        with self._lock:
            if self._epoll_fd >= 0 and _libc:
                os.close(self._epoll_fd)
                self._epoll_fd = -1
            for sock in list(self._socket_map.values()):
                try:
                    sock.close()
                except Exception:
                    pass
            self._socket_map.clear()
            self._callbacks.clear()
            self._buffers.clear()
