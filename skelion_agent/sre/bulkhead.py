import time
import threading
from typing import Optional, Dict, Any


class BulkheadOverloadError(Exception):
    """Raised when the adaptive bulkhead rejects a request due to saturation or concurrency limits."""
    pass


class AdaptiveBulkhead:
    """
    Ephemeral Adaptive Bulkhead Resource Isolation Engine with Dynamic Token Slicing.
    Protects agent pools from cascading resource starvation using non-blocking atomic
    primitives and sliding-window metrics.
    """

    def __init__(
        self,
        name: str,
        initial_concurrency: int = 10,
        min_concurrency: int = 2,
        max_concurrency: int = 100,
        target_latency_ms: float = 250.0,
        window_size: int = 50,
    ) -> None:
        self.name = name
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.target_latency_ms = target_latency_ms
        self.window_size = window_size

        self._current_concurrency = float(initial_concurrency)
        self._active_requests = 0
        self._latencies: list = []
        self._lock = threading.Lock()

    @property
    def active_requests(self) -> int:
        with self._lock:
            return self._active_requests

    @property
    def current_limit(self) -> int:
        with self._lock:
            return int(round(self._current_concurrency))

    def record_latency(self, latency_ms: float) -> None:
        """Record request latency and adjust concurrency dynamically."""
        with self._lock:
            self._latencies.append(latency_ms)
            if len(self._latencies) > self.window_size:
                self._latencies.pop(0)
            self._recalculate_limit_locked()

    def _recalculate_limit_locked(self) -> None:
        if not self._latencies:
            return

        # Compute p95 latency
        sorted_latencies = sorted(self._latencies)
        p95_idx = int(0.95 * len(sorted_latencies))
        p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]

        if p95_latency > self.target_latency_ms:
            # Shed load by reducing concurrency dynamically
            self._current_concurrency = max(
                float(self.min_concurrency),
                self._current_concurrency * 0.9,
            )
        else:
            # Expand concurrency headroom
            self._current_concurrency = min(
                float(self.max_concurrency),
                self._current_concurrency * 1.05,
            )

    def acquire(self) -> bool:
        """Attempt to acquire a concurrency slot non-blockingly."""
        with self._lock:
            limit = int(round(self._current_concurrency))
            if self._active_requests >= limit:
                return False
            self._active_requests += 1
            return True

    def release(self) -> None:
        """Release an acquired concurrency slot."""
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1

    def __enter__(self) -> "AdaptiveBulkhead":
        if not self.acquire():
            raise BulkheadOverloadError(f"Bulkhead '{self.name}' saturated. Concurrency limit reached.")
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.time() - getattr(self, "_start_time", time.time())) * 1000.0
        self.record_latency(duration_ms)
        self.release()
