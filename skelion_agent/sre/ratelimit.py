"""
Epoll-Based Adaptive Rate-Limiting Mesh with Token Bucket and Backpressure Propagation.

Provides high-throughput, non-blocking rate limiting and cascading backpressure signals
across agent boundaries using edge-triggered epoll notification loops.
"""

import os
import select
import socket
import struct
import threading
import time
import errno
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass(frozen=True)
class AdaptiveRateLimitConfig:
    """Configuration parameters for adaptive rate-limiting and backpressure mesh."""
    base_rate: float = 100.0
    max_rate: float = 1000.0
    min_rate: float = 10.0
    burst_capacity: float = 200.0
    telemetry_window_sec: float = 5.0
    backpressure_trigger_ratio: float = 0.85
    shedding_trigger_ratio: float = 0.95
    epoll_timeout_sec: float = 0.01


class TokenBucketMesh:
    """High-performance Token Bucket implementation with continuous O(1) time refill."""

    def __init__(self, capacity: float, refill_rate: float, initial_tokens: Optional[float] = None):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self, now: float) -> None:
        delta = max(0.0, now - self.last_update)
        if delta > 0.0:
            self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)
            self.last_update = now

    def update_rate(self, new_refill_rate: float) -> None:
        with self._lock:
            now = time.monotonic()
            self._refill(now)
            self.refill_rate = max(0.0, float(new_refill_rate))

    def consume(self, tokens: float = 1.0, now: Optional[float] = None) -> bool:
        ts = now if now is not None else time.monotonic()
        with self._lock:
            self._refill(ts)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class EpollAdaptiveMeshRateLimiter:
    """
    Epoll-backed adaptive rate limiter mesh that ingests real-time system telemetry,
    dynamically adjusts token refill rates, and propagates non-blocking backpressure signals.
    """

    def __init__(self, config: Optional[AdaptiveRateLimitConfig] = None):
        self.config = config or AdaptiveRateLimitConfig()
        self.bucket = TokenBucketMesh(
            capacity=self.config.burst_capacity,
            refill_rate=self.config.base_rate
        )
        self._running = False
        self._lock = threading.Lock()
        self._current_telemetry_load = 0.0
        self._backpressure_active = False
        self._shedding_active = False
        self._peer_sockets: Dict[int, socket.socket] = {}
        
        # Initialize epoll and non-blocking notification pipe if supported
        try:
            self._epoll = select.epoll()
            self._notify_read_fd, self._notify_write_fd = os.pipe()
            os.set_nonblock(self._notify_read_fd)
            os.set_nonblock(self._notify_write_fd)
            self._epoll.register(self._notify_read_fd, select.EPOLLIN)
            self._has_epoll = True
        except (AttributeError, OSError):
            self._has_epoll = False

        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            if self._has_epoll:
                self._thread = threading.Thread(target=self._epoll_loop, daemon=True)
                self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            if self._has_epoll:
                try:
                    os.write(self._notify_write_fd, b"STOP")
                except OSError:
                    pass
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._has_epoll:
            try:
                self._epoll.close()
            except Exception:
                pass
            try:
                os.close(self._notify_read_fd)
                os.close(self._notify_write_fd)
            except Exception:
                pass

    def _epoll_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                events = self._epoll.poll(self.config.epoll_timeout_sec)
                for fd, event in events:
                    if fd == self._notify_read_fd:
                        try:
                            os.read(self._notify_read_fd, 1024)
                        except OSError:
                            pass
            except (OSError, IOError) as e:
                if getattr(e, 'errno', None) != errno.EINTR:
                    break
            except Exception:
                break

    def ingest_telemetry(self, system_load_ratio: float) -> None:
        """
        Ingests real-time system telemetry load ratio [0.0, 1.0].
        Adjusts token refill rate dynamically and propagates backpressure if thresholds are breached.
        """
        ratio = max(0.0, min(1.0, float(system_load_ratio)))
        with self._lock:
            self._current_telemetry_load = ratio
            
            # Dynamic adaptive rate adjustment: higher load -> lower refill rate
            if ratio >= self.config.shedding_trigger_ratio:
                new_rate = self.config.min_rate
                self._shedding_active = True
                self._backpressure_active = True
            elif ratio >= self.config.backpressure_trigger_ratio:
                # Linear interpolation between min_rate and base_rate
                span = self.config.backpressure_trigger_ratio - self.config.shedding_trigger_ratio
                factor = max(0.0, 1.0 - ((ratio - self.config.backpressure_trigger_ratio) / (1.0 - self.config.backpressure_trigger_ratio + 1e-6)))
                new_rate = self.config.min_rate + factor * (self.config.base_rate - self.config.min_rate)
                self._shedding_active = False
                self._backpressure_active = True
            else:
                # Scale up towards max_rate under low load
                factor = 1.0 - (ratio / (self.config.backpressure_trigger_ratio + 1e-6))
                new_rate = self.config.base_rate + factor * (self.config.max_rate - self.config.base_rate)
                self._shedding_active = False
                self._backpressure_active = False

            self.bucket.update_rate(new_rate)

        if self._backpressure_active:
            self._propagate_backpressure()

    def _propagate_backpressure(self) -> None:
        """Propagates non-blocking backpressure signal to connected upstream peer sockets."""
        signal_payload = struct.pack("!Bf", 0xFF, self._current_telemetry_load)
        with self._lock:
            sockets_to_prune = []
            for fd, sock in self._peer_sockets.items():
                try:
                    sock.setblocking(False)
                    sock.send(signal_payload)
                except (BlockingIOError, socket.error, OSError):
                    # Non-blocking socket saturated or disconnected; ignore or prune
                    pass
                except Exception:
                    sockets_to_prune.append(fd)
            for fd in sockets_to_prune:
                self._peer_sockets.pop(fd, None)

    def register_peer_socket(self, sock: socket.socket) -> None:
        """Registers an upstream peer socket for backpressure propagation."""
        try:
            sock.setblocking(False)
            fd = sock.fileno()
            with self._lock:
                self._peer_sockets[fd] = sock
        except Exception:
            pass

    def unregister_peer_socket(self, sock: socket.socket) -> None:
        """Unregisters an upstream peer socket."""
        try:
            fd = sock.fileno()
            with self._lock:
                self._peer_sockets.pop(fd, None)
        except Exception:
            pass

    def acquire(self, tokens: float = 1.0) -> bool:
        """Attempts to acquire tokens from the adaptive rate-limiting mesh."""
        if self._shedding_active:
            return False
        return self.bucket.consume(tokens)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns telemetry metrics for observability."""
        with self._lock:
            return {
                "current_load": self._current_telemetry_load,
                "refill_rate": self.bucket.refill_rate,
                "tokens_available": self.bucket.tokens,
                "backpressure_active": self._backpressure_active,
                "shedding_active": self._shedding_active,
                "registered_peers": len(self._peer_sockets)
            }
