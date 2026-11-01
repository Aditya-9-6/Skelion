import select
import socket
import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Callable, Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BulkheadConfig:
    max_concurrent: int = 50
    queue_capacity: int = 100
    acquire_timeout: float = 2.0
    heartbeat_interval: float = 1.0
    leader_lease_timeout: float = 3.0


class BulkheadLease:
    def __init__(self, bulkhead: 'EpollBulkheadMesh', resource_pool: str):
        self.bulkhead = bulkhead
        self.resource_pool = resource_pool
        self.acquired = False

    def __enter__(self) -> 'BulkheadLease':
        self.acquired = self.bulkhead.acquire(self.resource_pool)
        if not self.acquired:
            raise TimeoutError(f"Bulkhead acquisition timed out or pool '{self.resource_pool}' saturated.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.acquired:
            self.bulkhead.release(self.resource_pool)


class EpollBulkheadMesh:
    """
    Epoll-driven non-blocking bulkhead isolation engine that dynamically distributes
    concurrency quotas across resource pools using an ephemeral leader-election heartbeat protocol.
    """
    def __init__(self, node_id: str, config: Optional[BulkheadConfig] = None) -> None:
        self.node_id = node_id
        self.config = config or BulkheadConfig()
        self._lock = threading.RLock()
        
        # Pool metrics and concurrency bounds
        self._active_counts: Dict[str, int] = {}
        self._queue_counts: Dict[str, int] = {}
        self._pool_configs: Dict[str, BulkheadConfig] = {}
        
        # Epoll and non-blocking socket pairs for event notification
        self._epoll = select.epoll()
        self._wake_sockets: Dict[str, socket.socket] = {}
        self._listener_sockets: Dict[str, socket.socket] = {}
        
        # Leader election state
        self._leaders: Dict[str, str] = {}
        self._last_heartbeats: Dict[str, float] = {}
        
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def register_pool(self, resource_pool: str, config: Optional[BulkheadConfig] = None) -> None:
        with self._lock:
            cfg = config or self.config
            self._pool_configs[resource_pool] = cfg
            self._active_counts.setdefault(resource_pool, 0)
            self._queue_counts.setdefault(resource_pool, 0)
            
            if resource_pool not in self._wake_sockets:
                server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_sock.bind(('127.0.0.1', 0))
                server_sock.listen(1)
                server_sock.setblocking(False)
                
                client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_sock.connect(server_sock.getsockname())
                client_sock.setblocking(False)
                
                conn, _ = server_sock.accept()
                conn.setblocking(False)
                
                self._listener_sockets[resource_pool] = server_sock
                self._wake_sockets[resource_pool] = conn
                
                self._epoll.register(conn.fileno(), select.EPOLLIN)

    def acquire(self, resource_pool: str, timeout: Optional[float] = None) -> bool:
        with self._lock:
            if resource_pool not in self._pool_configs:
                self.register_pool(resource_pool)
            
            cfg = self._pool_configs[resource_pool]
            t_out = timeout if timeout is not None else cfg.acquire_timeout
            start_time = time.monotonic()
            
            while True:
                active = self._active_counts.get(resource_pool, 0)
                if active < cfg.max_concurrent:
                    self._active_counts[resource_pool] = active + 1
                    return True
                
                queued = self._queue_counts.get(resource_pool, 0)
                if queued >= cfg.queue_capacity:
                    return False
                
                self._queue_counts[resource_pool] = queued + 1
                
                elapsed = time.monotonic() - start_time
                remaining = t_out - elapsed
                if remaining <= 0:
                    self._queue_counts[resource_pool] -= 1
                    return False
                
                self._lock.release()
                try:
                    events = self._epoll.poll(timeout=remaining)
                    for fileno, _ in events:
                        for pool, sock in self._wake_sockets.items():
                            if sock.fileno() == fileno:
                                try:
                                    sock.recv(1024)
                                except BlockingIOError:
                                    pass
                finally:
                    self._lock.acquire()
                
                self._queue_counts[resource_pool] = max(0, self._queue_counts.get(resource_pool, 1) - 1)

    def release(self, resource_pool: str) -> None:
        with self._lock:
            active = self._active_counts.get(resource_pool, 0)
            if active > 0:
                self._active_counts[resource_pool] = active - 1
            
            if resource_pool in self._wake_sockets:
                try:
                    self._wake_sockets[resource_pool].send(b'x')
                except (BlockingIOError, BrokenPipeError):
                    pass

    def lease(self, resource_pool: str) -> BulkheadLease:
        return BulkheadLease(self, resource_pool)

    def heartbeat(self, resource_pool: str, candidate_node: str) -> bool:
        with self._lock:
            now = time.time()
            current_leader = self._leaders.get(resource_pool)
            last_hb = self._last_heartbeats.get(resource_pool, 0.0)
            cfg = self._pool_configs.get(resource_pool, self.config)
            
            if not current_leader or (now - last_hb) > cfg.leader_lease_timeout or current_leader == candidate_node:
                self._leaders[resource_pool] = candidate_node
                self._last_heartbeats[resource_pool] = now
                return True
            return False

    def get_leader(self, resource_pool: str) -> Optional[str]:
        with self._lock:
            now = time.time()
            current_leader = self._leaders.get(resource_pool)
            last_hb = self._last_heartbeats.get(resource_pool, 0.0)
            cfg = self._pool_configs.get(resource_pool, self.config)
            
            if current_leader and (now - last_hb) <= cfg.leader_lease_timeout:
                return current_leader
            return None

    def close(self) -> None:
        with self._lock:
            for pool, sock in self._wake_sockets.items():
                try:
                    self._epoll.unregister(sock.fileno())
                    sock.close()
                except Exception:
                    pass
            for pool, sock in self._listener_sockets.items():
                try:
                    sock.close()
                except Exception:
                    pass
            try:
                self._epoll.close()
            except Exception:
                pass
