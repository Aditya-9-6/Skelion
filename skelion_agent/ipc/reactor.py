import select
import socket
import logging
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)


class EpollReactor:
    """
    High-performance epoll-driven event notification reactor for sub-millisecond
    asynchronous IPC and network telemetry multiplexing.
    """

    def __init__(self):
        self._has_epoll = hasattr(select, "epoll")
        self._epoll = select.epoll() if self._has_epoll else None
        self._handlers: Dict[int, Callable[[int, int], None]] = {}
        self._read_fds: Dict[int, socket.socket] = {}

    def register(
        self, fd_obj: Any, events: int, handler: Callable[[int, int], None]
    ) -> None:
        """Register a file descriptor or socket with the epoll reactor."""
        fd = fd_obj.fileno() if hasattr(fd_obj, "fileno") else int(fd_obj)
        self._handlers[fd] = handler
        if hasattr(fd_obj, "makefile") or isinstance(fd_obj, socket.socket):
            self._read_fds[fd] = fd_obj

        if self._has_epoll:
            self._epoll.register(fd, events)
        else:
            logger.debug(
                "epoll not available, falling back to select simulation for fd %d", fd
            )

    def unregister(self, fd_obj: Any) -> None:
        """Unregister a file descriptor from the reactor."""
        fd = fd_obj.fileno() if hasattr(fd_obj, "fileno") else int(fd_obj)
        self._handlers.pop(fd, None)
        self._read_fds.pop(fd, None)

        if self._has_epoll:
            try:
                self._epoll.unregister(fd)
            except Exception:
                pass

    def poll(self, timeout: float = 0.1) -> int:
        """Poll for registered file descriptor events and dispatch callbacks."""
        if self._has_epoll:
            events = self._epoll.poll(timeout)
            for fd, event in events:
                handler = self._handlers.get(fd)
                if handler:
                    handler(fd, event)
            return len(events)
        else:
            if not self._read_fds:
                return 0
            rlist = list(self._read_fds.values())
            readable, _, _ = select.select(rlist, [], [], timeout)
            count = 0
            for s in readable:
                fd = s.fileno()
                handler = self._handlers.get(fd)
                if handler:
                    handler(fd, select.EPOLLIN if hasattr(select, "EPOLLIN") else 1)
                    count += 1
            return count

    def close(self) -> None:
        if self._has_epoll and self._epoll:
            try:
                self._epoll.close()
            except Exception:
                pass
