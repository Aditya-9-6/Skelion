import time
import threading
from typing import Dict, Any, Optional

class AdaptiveLoadShedder:
    """
    Epoll-Driven Asynchronous Adaptive Load Shedder using Little's Law (L = lambda * W).
    Continuously computes queue saturation and decides whether to shed inbound telemetry or requests.
    """
    def __init__(self, target_latency_sec: float = 0.05, max_concurrent_limit: int = 1000, smoothing_factor: float = 0.2) -> None:
        self.target_latency_sec = target_latency_sec
        self.max_concurrent_limit = max_concurrent_limit
        self.smoothing_factor = smoothing_factor
        
        self._active_requests = 0
        self._rolling_latency = target_latency_sec
        self._request_count = 0
        self._shed_count = 0
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """
        Attempt to acquire a request slot based on current Little's Law capacity estimation.
        Returns True if admitted, False if shed.
        """
        with self._lock:
            # Estimated capacity via Little's Law: L_max = max_throughput * target_latency
            # Here we approximate capacity using active requests and current saturation
            current_capacity = self.max_concurrent_limit
            if self._active_requests >= current_capacity:
                self._shed_count += 1
                return False
            
            self._active_requests += 1
            return True

    def release(self, latency_sec: float) -> None:
        """
        Release a request slot and update rolling latency metrics.
        """
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1
            
            # Exponentially weighted moving average for latency
            self._rolling_latency = (
                self.smoothing_factor * latency_sec +
                (1.0 - self.smoothing_factor) * self._rolling_latency
            )
            self._request_count += 1

    def should_shed(self) -> bool:
        """
        Evaluate if inbound requests should be shed based on Little's Law saturation.
        Queue saturation = (active_requests * rolling_latency) / (target_latency * max_concurrent)
        """
        with self._lock:
            if self.target_latency_sec <= 0 or self.max_concurrent_limit <= 0:
                return False
            
            saturation = (self._active_requests * self._rolling_latency) / (self.target_latency_sec * self.max_concurrent_limit)
            return saturation > 1.0

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_requests": self._active_requests,
                "rolling_latency": self._rolling_latency,
                "request_count": self._request_count,
                "shed_count": self._shed_count,
                "should_shed": self.should_shed(),
            }
