import time
import threading
from typing import Optional, Dict, Any


class AdaptiveConcurrencyThrottler:
    """
    Adaptive Concurrency Throttler with Bounded Token Bucket.
    Dynamically throttles non-critical ingress routes when CPU or memory exhaustion exceeds safe thresholds.
    Optimized for high throughput, low memory footprint, and thread safety under concurrent load.
    """

    def __init__(
        self,
        max_tokens: float = 100.0,
        refill_rate: float = 10.0,
        cpu_threshold: float = 85.0,
        memory_threshold: float = 85.0,
    ):
        self.max_tokens = float(max_tokens)
        self.tokens = float(max_tokens)
        self.refill_rate = float(refill_rate)  # tokens per second
        self.cpu_threshold = float(cpu_threshold)
        self.memory_threshold = float(memory_threshold)

        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._metrics: Dict[str, Any] = {
            "total_requests": 0,
            "dropped_requests": 0,
            "passed_requests": 0,
        }

    def _refill(self, now: float) -> None:
        elapsed = now - self._last_refill
        if elapsed > 0:
            added = elapsed * self.refill_rate
            self.tokens = min(self.max_tokens, self.tokens + added)
            self._last_refill = now

    def acquire(
        self, cpu_load: float = 0.0, memory_load: float = 0.0, cost: float = 1.0
    ) -> bool:
        """
        Attempt to acquire tokens for an incoming request.
        Sheds traffic automatically if system health indicators exceed thresholds or token bucket is exhausted.
        """
        with self._lock:
            self._metrics["total_requests"] += 1

            # Automatic traffic shedding if system is overloaded
            if cpu_load >= self.cpu_threshold or memory_load >= self.memory_threshold:
                self._metrics["dropped_requests"] += 1
                return False

            now = time.monotonic()
            self._refill(now)

            if self.tokens >= cost:
                self.tokens -= cost
                self._metrics["passed_requests"] += 1
                return True
            else:
                self._metrics["dropped_requests"] += 1
                return False

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._metrics)

    def update_config(
        self,
        max_tokens: Optional[float] = None,
        refill_rate: Optional[float] = None,
        cpu_threshold: Optional[float] = None,
        memory_threshold: Optional[float] = None,
    ) -> None:
        with self._lock:
            if max_tokens is not None:
                self.max_tokens = float(max_tokens)
                self.tokens = min(self.tokens, self.max_tokens)
            if refill_rate is not None:
                self.refill_rate = float(refill_rate)
            if cpu_threshold is not None:
                self.cpu_threshold = float(cpu_threshold)
            if memory_threshold is not None:
                self.memory_threshold = float(memory_threshold)
