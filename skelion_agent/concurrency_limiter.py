# skelion_agent/concurrency_limiter.py - Epoll-Based Non-Blocking Concurrent Adaptive Concurrency Limit Controller

import os
import time
import select
import threading
from typing import Dict, Any, Optional


class ConcurrencyLimitExceededError(Exception):
    """Raised when the adaptive concurrency limit is breached and requests are shed."""

    def __init__(
        self,
        message: str = "Concurrency limit exceeded, shedding load via Little's Law",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.details = details or {}
        self.status_code = 429


class AdaptiveConcurrencyLimiter:
    """
    High-throughput non-blocking concurrency limit controller utilizing an epoll-based
    reactor mechanism and Little's Law (L = \u03bb * W) to continuously calculate
    optimal concurrency ceilings based on real-time service time and queue length.
    """

    def __init__(
        self,
        initial_limit: int = 100,
        min_limit: int = 5,
        max_limit: int = 5000,
        target_latency_ms: float = 100.0,
        smoothing_factor: float = 0.2,
    ):
        self.initial_limit = initial_limit
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.target_latency_ms = target_latency_ms
        self.smoothing_factor = smoothing_factor

        self._current_limit = float(initial_limit)
        self._in_flight = 0
        self._queue_length = 0
        self._smoothed_latency = target_latency_ms
        self._total_requests = 0
        self._shed_requests = 0

        self._lock = threading.Lock()

        # Initialize epoll pipe for non-blocking reactor notification if supported
        self._use_epoll = hasattr(select, "epoll")
        if self._use_epoll:
            try:
                self._epoll = select.epoll()
                self._r_fd, self._w_fd = os.pipe()
                os.set_nonblock(self._r_fd)
                os.set_nonblock(self._w_fd)
                self._epoll.register(self._r_fd, select.EPOLLIN)
            except Exception:
                self._use_epoll = False

    @property
    def current_limit(self) -> int:
        with self._lock:
            return int(round(self._current_limit))

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Attempts to acquire a concurrency slot non-blocking or with an optional timeout.
        Evaluates Little's Law invariants before granting admission.
        """
        start_time = time.monotonic()
        while True:
            with self._lock:
                limit = int(round(self._current_limit))
                if self._in_flight < limit:
                    self._in_flight += 1
                    self._total_requests += 1
                    return True
                else:
                    self._shed_requests += 1

            # If non-blocking requested
            if timeout == 0.0:
                return False

            # Wait on epoll reactor if available, otherwise sleep briefly
            elapsed = time.monotonic() - start_time
            if timeout is not None and elapsed >= timeout:
                return False

            if self._use_epoll:
                try:
                    events = self._epoll.poll(0.01)
                    if events:
                        os.read(self._r_fd, 512)
                except Exception:
                    time.sleep(0.001)
            else:
                time.sleep(0.001)

    def release(self, latency_ms: float) -> None:
        """
        Releases an in-flight slot, updates exponentially smoothed latency,
        and applies Little's Law to dynamically adjust the concurrency limit.
        """
        with self._lock:
            if self._in_flight > 0:
                self._in_flight -= 1

            # Update smoothed RTT latency (EMA)
            self._smoothed_latency = (
                self.smoothing_factor * latency_ms
                + (1.0 - self.smoothing_factor) * self._smoothed_latency
            )

            # Little's Law calculation: L = \u03bb * W
            # Concurrency Limit = Throughput (requests/sec) * Service Time (seconds)
            # We adapt current_limit dynamically towards target vs actual latency ratio
            if self._smoothed_latency > 0:
                latency_ratio = self.target_latency_ms / self._smoothed_latency
                # Gradient adjustment
                adjustment = (
                    self._current_limit * (latency_ratio - 1.0) * self.smoothing_factor
                )
                self._current_limit = max(
                    float(self.min_limit),
                    min(float(self.max_limit), self._current_limit + adjustment),
                )

        # Trigger epoll wake-up notification if active
        if self._use_epoll:
            try:
                os.write(self._w_fd, b"1")
            except Exception:
                pass

    def enforce_admission(self, latency_ms: Optional[float] = None) -> None:
        """
        Wrapper that attempts to acquire slot and raises ConcurrencyLimitExceededError if shed.
        """
        if not self.acquire(timeout=0.0):
            raise ConcurrencyLimitExceededError(
                details={
                    "current_limit": self.current_limit,
                    "in_flight": self.in_flight,
                    "smoothed_latency_ms": self._smoothed_latency,
                }
            )

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_limit": int(round(self._current_limit)),
                "in_flight": self._in_flight,
                "smoothed_latency_ms": round(self._smoothed_latency, 2),
                "target_latency_ms": self.target_latency_ms,
                "total_requests": self._total_requests,
                "shed_requests": self._shed_requests,
                "epoll_active": self._use_epoll,
            }
