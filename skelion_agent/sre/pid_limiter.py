import time
import threading
from typing import Dict, Any


class AdaptivePIDLimiter:
    """
    High-performance Adaptive PID Controller for concurrency limiting and cascading failure prevention.
    Monitors queue depth, latency, and drop rates using sub-millisecond control loop adjustments.
    """

    def __init__(
        self,
        target_latency: float = 0.05,
        kp: float = 1.2,
        ki: float = 0.1,
        kd: float = 0.05,
        min_concurrency: int = 10,
        max_concurrency: int = 10000,
    ):
        self.target_latency = float(target_latency)
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.min_concurrency = int(min_concurrency)
        self.max_concurrency = int(max_concurrency)

        self._current_limit = float(max_concurrency)
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time = time.monotonic()
        self._lock = threading.Lock()
        self._drop_count = 0
        self._success_count = 0

    def update(
        self, current_latency: float, queue_depth: int, dropped: bool = False
    ) -> int:
        """
        Updates the PID controller state given current latency and queue telemetry.
        Returns the adjusted concurrency limit.
        """
        with self._lock:
            now = time.monotonic()
            dt = now - self._last_time
            if dt <= 0.0:
                dt = 0.001
            self._last_time = now

            if dropped:
                self._drop_count += 1
            else:
                self._success_count += 1

            # Error calculation: positive error means latency is higher than target
            error = current_latency - self.target_latency

            # Proportional term
            p_term = self.kp * error

            # Integral term with anti-windup clamping
            self._integral += error * dt
            self._integral = max(-100.0, min(100.0, self._integral))
            i_term = self.ki * self._integral

            # Derivative term
            d_term = self.kd * (error - self._prev_error) / dt
            self._prev_error = error

            # Adjustment delta
            adjustment = p_term + i_term + d_term

            # Adjust concurrency limit inversely to error (higher latency -> lower concurrency)
            self._current_limit -= adjustment * self._current_limit

            # Queue saturation feedback adjustment
            if queue_depth > 500:
                self._current_limit *= 0.95
            elif queue_depth < 50:
                self._current_limit *= 1.05

            # Bounded limits
            self._current_limit = max(
                float(self.min_concurrency),
                min(float(self.max_concurrency), self._current_limit),
            )
            return int(self._current_limit)

    def get_limit(self) -> int:
        with self._lock:
            return int(self._current_limit)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_limit": int(self._current_limit),
                "target_latency": self.target_latency,
                "drop_count": self._drop_count,
                "success_count": self._success_count,
                "integral": self._integral,
            }
