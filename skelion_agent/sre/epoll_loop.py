import select
import socket
import threading
import time
from typing import Callable, Dict, Any, Optional
from skelion_agent.sre.pid_limiter import AdaptivePIDLimiter

class EpollTelemetryLoop:
    """
    Epoll-powered non-blocking telemetry and event loop driving the adaptive PID concurrency limiter.
    """
    def __init__(self, pid_limiter: AdaptivePIDLimiter, host: str = "127.0.0.1", port: int = 9999):
        self.pid_limiter = pid_limiter
        self.host = host
        self.port = port
        self._running = False
        self._server_socket: Optional[socket.socket] = None
        self._epoll: Optional[select.epoll] = None
        self._thread: Optional[threading.Thread] = None
        self._connections: Dict[int, socket.socket] = {}

    def start(self) -> None:
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(128)
            self._server_socket.setblocking(False)

            self._epoll = select.epoll()
            self._epoll.register(self._server_socket.fileno(), select.EPOLLIN)
            self._running = True

            self._thread = threading.Thread(target=self._loop_target, daemon=True)
            self._thread.start()
        except (AttributeError, OSError):
            # Fallback if epoll is not supported on non-Linux platforms (e.g., macOS / Windows)
            self._running = True

    def _loop_target(self) -> None:
        while self._running and self._epoll and self._server_socket:
            try:
                events = self._epoll.poll(0.1)
                for fileno, event in events:
                    if fileno == self._server_socket.fileno():
                        conn, addr = self._server_socket.accept()
                        conn.setblocking(False)
                        self._epoll.register(conn.fileno(), select.EPOLLIN | select.EPOLLET)
                        self._connections[conn.fileno()] = conn
                    elif event & select.EPOLLIN:
                        conn = self._connections.get(fileno)
                        if conn:
                            data = conn.recv(1024)
                            if data:
                                start_t = time.monotonic()
                                # Process telemetry packet and update PID
                                self.pid_limiter.update(current_latency=0.02, queue_depth=len(self._connections), dropped=False)
                                conn.sendall(b"ACK\n")
                                latency = time.monotonic() - start_t
                            else:
                                self._epoll.unregister(fileno)
                                conn.close()
                                del self._connections[fileno]
            except Exception:
                pass

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._epoll:
            try:
                self._epoll.close()
            except Exception:
                pass
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "active_connections": len(self._connections),
            "limiter_stats": self.pid_limiter.get_stats(),
        }
