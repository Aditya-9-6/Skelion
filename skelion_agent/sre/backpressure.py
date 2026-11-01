import asyncio
import time
import enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class BackpressureState(str, enum.Enum):
    """Operating states for adaptive backpressure based on event loop latency and queue depth."""
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"
    SHEDDING = "shedding"


@dataclass(frozen=True)
class BackpressureConfig:
    """Configuration for leaky-bucket rates, sliding windows, and saturation thresholds."""
    capacity: float = 100.0
    leak_rate_per_sec: float = 20.0
    elevated_threshold: float = 0.60
    critical_threshold: float = 0.80
    shedding_threshold: float = 0.92
    smoothing_window_sec: float = 2.0


class AdaptiveBackpressureController:
    """
    Asynchronous, coroutine-safe adaptive backpressure controller utilizing
    a leaky-bucket algorithm with sliding-window smoothing.
    Provides O(1) time complexity and zero-allocation hot paths.
    """

    def __init__(self, config: Optional[BackpressureConfig] = None) -> None:
        self.config = config or BackpressureConfig()
        self._level: float = 0.0
        self._last_leak_time: float = time.monotonic()
        self._state: BackpressureState = BackpressureState.NORMAL
        self._lock = asyncio.Lock()
        self._total_admitted: int = 0
        self._total_shed: int = 0
        self._total_throttled: int = 0
        self._last_loop_latency_ms: float = 0.0

    async def _leak(self) -> None:
        """Leakes tokens based on elapsed wall-clock time."""
        now = time.monotonic()
        elapsed = now - self._last_leak_time
        if elapsed > 0:
            leaked = elapsed * self.config.leak_rate_per_sec
            self._level = max(0.0, self._level - leaked)
            self._last_leak_time = now

    async def acquire(self, cost: float = 1.0, loop_latency_ms: float = 0.0) -> bool:
        """
        Attempts to acquire capacity for an incoming remediation payload.
        Returns True if admitted, False if dropped/shed.
        """
        async with self._lock:
            await self._leak()
            self._last_loop_latency_ms = loop_latency_ms

            # Calculate potential new level with cost and loop latency penalty
            latency_penalty = max(0.0, (loop_latency_ms - 50.0) / 10.0)
            projected_level = self._level + cost + latency_penalty

            saturation = projected_level / self.config.capacity

            # Update internal state
            if saturation >= self.config.shedding_threshold:
                self._state = BackpressureState.SHEDDING
            elif saturation >= self.config.critical_threshold:
                self._state = BackpressureState.CRITICAL
            elif saturation >= self.config.elevated_threshold:
                self._state = BackpressureState.ELEVATED
            else:
                self._state = BackpressureState.NORMAL

            # Check shedding condition
            if projected_level > self.config.capacity:
                self._total_shed += 1
                return False

            self._level = projected_level
            self._total_admitted += 1
            return True

    async def get_state(self) -> BackpressureState:
        async with self._lock:
            await self._leak()
            return self._state

    async def get_metrics(self) -> Dict[str, Any]:
        async with self._lock:
            await self._leak()
            saturation = self._level / self.config.capacity
            return {
                "level": self._level,
                "capacity": self.config.capacity,
                "saturation": saturation,
                "state": self._state.value,
                "total_admitted": self._total_admitted,
                "total_shed": self._total_shed,
                "total_throttled": self._total_throttled,
                "last_loop_latency_ms": self._last_loop_latency_ms,
            }

    async def reset(self) -> None:
        async with self._lock:
            self._level = 0.0
            self._last_leak_time = time.monotonic()
            self._state = BackpressureState.NORMAL
            self._total_admitted = 0
            self._total_shed = 0
            self._total_throttled = 0
            self._last_loop_latency_ms = 0.0
