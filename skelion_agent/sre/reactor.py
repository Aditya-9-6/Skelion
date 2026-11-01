import select
import socket
import logging
from typing import Callable, Dict, Any, Optional
from skelion_agent.sre.load_shedder import AdaptiveLoadShedder

logger = logging.getLogger(__name__)

class EpollReactorMesh:
    """
    Epoll-driven reactor mesh integrating adaptive load shedding with network socket multiplexing.
    """
    def __init__(self, load_shedder: Optional[AdaptiveLoadShedder] = None) -> None:
        self.load_shedder = load_shedder or AdaptiveLoadShedder()
        self.epoll = select.epoll()
        self.fd_map: Dict[int, socket.socket] = {}
        self._running = False

    def register_socket(self, sock: socket.socket, events: int = select.EPOLLIN) -> None:
        sock.setblocking(False)
        fd = sock.fileno()
        self.fd_map[fd] = sock
        self.epoll.register(fd, events)

    def unregister_socket(self, sock: socket.socket) -> None:
        fd = sock.fileno()
        if fd in self.fd_map:
            self.epoll.unregister(fd)
            del self.fd_map[fd]

    def evaluate_inbound(self) -> bool:
        """
        Evaluate load shedder before accepting or processing an inbound connection.
        Returns True if processing is allowed, False if shed.
        """
        return self.load_shedder.acquire()

    def complete_request(self, latency_sec: float) -> None:
        self.load_shedder.release(latency_sec)

    def close(self) -> None:
        try:
            self.epoll.close()
        except Exception:
            pass
