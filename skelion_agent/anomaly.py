import math
import threading
from collections import deque
from typing import Deque, Tuple, Optional, Dict


class WelfordOnlineStats:
    """Thread-safe online mean and variance accumulator using Welford's algorithm."""

    def __init__(self) -> None:
        self.count: int = 0
        self.mean: float = 0.0
        self._m2: float = 0.0
        self._lock = threading.Lock()

    def update(self, value: float) -> None:
        with self._lock:
            self.count += 1
            delta = value - self.mean
            self.mean += delta / self.count
            delta2 = value - self.mean
            self._m2 += delta * delta2

    def reset(self) -> None:
        with self._lock:
            self.count = 0
            self.mean = 0.0
            self._m2 = 0.0

    @property
    def variance(self) -> float:
        with self._lock:
            if self.count < 2:
                return 0.0
            return self._m2 / (self.count - 1)

    @property
    def standard_deviation(self) -> float:
        var = self.variance
        return math.sqrt(var) if var > 0.0 else 0.0

    def get_snapshot(self) -> Tuple[int, float, float]:
        with self._lock:
            return self.count, self.mean, self.standard_deviation


class SlidingZScoreFilter:
    """Sliding window Z-Score anomaly detector for streaming metrics."""

    def __init__(self, window_size: int = 100, threshold: float = 3.0) -> None:
        self.window_size = window_size
        self.threshold = threshold
        self.window: Deque[float] = deque(maxlen=window_size)
        self.stats = WelfordOnlineStats()
        self._lock = threading.Lock()

    def add(self, value: float) -> Tuple[bool, float]:
        """
        Add a new sample to the sliding window, update statistics,
        and determine if the value is an outlier anomaly.
        Returns: (is_anomaly, computed_z_score)
        """
        with self._lock:
            # If window is at capacity, we could rebuild or approximate.
            # For exact sliding window stats with Welford, we manage a deque and recalculate or slide.
            # Given high-throughput constraints and typical sliding window sizes (e.g. 100-1000),
            # recalculating or maintaining full stats on eviction is robust and accurate.
            if len(self.window) >= self.window_size:
                self.window.popleft()
            
            self.window.append(value)
            
            # Recompute Welford stats over current window for accuracy
            count = len(self.window)
            if count < 5:
                # Insufficient sample size for reliable Z-score
                return False, 0.0

            # Fast recomputation
            mean = sum(self.window) / count
            variance = sum((x - mean) ** 2 for x in self.window) / (count - 1) if count > 1 else 0.0
            std_dev = math.sqrt(variance) if variance > 0.0 else 0.0

            if std_dev == 0.0:
                is_anomaly = abs(value - mean) > 1e-9
                z_score = 0.0 if not is_anomaly else float('inf')
                return is_anomaly, z_score

            z_score = (value - mean) / std_dev
            is_anomaly = abs(z_score) >= self.threshold
            return is_anomaly, z_score

    def get_window_stats(self) -> Dict[str, float]:
        with self._lock:
            count = len(self.window)
            if count == 0:
                return {"count": 0,
                        "mean": 0.0,
                        "std_dev": 0.0}
            mean = sum(self.window) / count
            variance = sum((x - mean) ** 2 for x in self.window) / (count - 1) if count > 1 else 0.0
            return {
                "count": count,
                "mean": mean,
                "std_dev": math.sqrt(variance)
            }
