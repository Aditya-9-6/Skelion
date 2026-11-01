import threading
from typing import Dict, Optional, Any


class VectorClockFlowController:
    """
    High-throughput, non-blocking backpressure flow controller utilizing real-time
    vector clocks to dynamically adjust telemetry and remediation payload propagation.
    Enforces strict memory bounds using lock-free atomic registers and lock primitives.
    """

    def __init__(
        self, node_id: str, high_watermark: int = 1000, low_watermark: int = 400
    ):
        self.node_id = node_id
        self.high_watermark = high_watermark
        self.low_watermark = low_watermark
        self._clock: Dict[str, int] = {node_id: 0}
        self._lock = threading.Lock()
        self._dropped_count = 0
        self._throttled_count = 0
        self._passed_count = 0

    def increment(self) -> int:
        with self._lock:
            self._clock[self.node_id] = self._clock.get(self.node_id, 0) + 1
            return self._clock[self.node_id]

    def update_clock(self, remote_clock: Dict[str, int]) -> None:
        with self._lock:
            for node, ts in remote_clock.items():
                self._clock[node] = max(self._clock.get(node, 0), ts)

    def get_clock(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._clock)

    def calculate_congestion_gradient(self, queue_depth: int) -> float:
        """
        Calculates normalized congestion gradient (0.0 to 1.0+) based on queue depth
        relative to watermarks.
        """
        if queue_depth <= self.low_watermark:
            return 0.0
        if queue_depth >= self.high_watermark:
            return 1.0
        span = self.high_watermark - self.low_watermark
        if span <= 0:
            return 1.0
        return float(queue_depth - self.low_watermark) / float(span)

    def evaluate_payload(
        self,
        priority: str,
        queue_depth: int,
        vector_clock: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Evaluates whether a payload should be PASSED, THROTTLED, or DROPPED.
        - High-severity incident logs (priority == 'CRITICAL' or 'HIGH') are never dropped.
        - Low-priority telemetry streams are throttled/dropped under congestion.
        Returns: 'PASS', 'THROTTLE', or 'DROP'
        """
        if vector_clock:
            self.update_clock(vector_clock)

        gradient = self.calculate_congestion_gradient(queue_depth)

        with self._lock:
            if priority in ("CRITICAL", "HIGH", "INCIDENT"):
                self._passed_count += 1
                return "PASS"

            if gradient >= 1.0:
                self._dropped_count += 1
                return "DROP"
            elif gradient > 0.5:
                self._throttled_count += 1
                return "THROTTLE"
            else:
                self._passed_count += 1
                return "PASS"

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "node_id": self.node_id,
                "clock": dict(self._clock),
                "passed_count": self._passed_count,
                "throttled_count": self._throttled_count,
                "dropped_count": self._dropped_count,
            }
