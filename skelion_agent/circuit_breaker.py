import time
import random
import threading
from typing import Optional, Dict, Any
from enum import Enum

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class RingBuffer:
    __slots__ = ('capacity', 'buffer', 'head', 'size', 'lock')
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = [0.0] * capacity
        self.head = 0
        self.size = 0
        self.lock = threading.Lock()
        
    def append(self, val: float) -> None:
        with self.lock:
            self.buffer[self.head] = val
            self.head = (self.head + 1) % self.capacity
            if self.size < self.capacity:
                self.size += 1
                
    def get_values(self) -> list[float]:
        with self.lock:
            if self.size == 0:
                return []
            if self.size < self.capacity:
                return self.buffer[:self.size]
            return self.buffer[self.head:] + self.buffer[:self.head]
            
    def clear(self) -> None:
        with self.lock:
            self.head = 0
            self.size = 0

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_rate_threshold: float = 0.5,
        window_size: int = 100,
        recovery_timeout: float = 5.0,
        half_open_max_probes: int = 5,
        backoff_multiplier: float = 2.0,
        max_backoff: float = 60.0,
        jitter: bool = True,
    ):
        self.name = name
        self.failure_rate_threshold = failure_rate_threshold
        self.window_size = window_size
        self.recovery_timeout = recovery_timeout
        self.half_open_max_probes = half_open_max_probes
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff = max_backoff
        self.jitter = jitter
        
        self.state = CircuitState.CLOSED
        self._ring = RingBuffer(window_size)
        self._lock = threading.Lock()
        
        self._failure_count = 0
        self._next_attempt_time = 0.0
        self._current_backoff = recovery_timeout
        self._half_open_successes = 0
        self._half_open_probes_in_flight = 0

    def _calculate_error_rate(self) -> float:
        vals = self._ring.get_values()
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    def allow_request(self) -> bool:
        with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if now >= self._next_attempt_time:
                    self.state = CircuitState.HALF_OPEN
                    self._half_open_successes = 0
                    self._half_open_probes_in_flight = 1
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                if self._half_open_probes_in_flight < self.half_open_max_probes:
                    self._half_open_probes_in_flight += 1
                    return True
                return False
            else:
                return True

    def record_success(self) -> None:
        with self._lock:
            self._ring.append(0.0)
            if self.state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                self._half_open_probes_in_flight = max(0, self._half_open_probes_in_flight - 1)
                if self._half_open_successes >= self.half_open_max_probes:
                    self.state = CircuitState.CLOSED
                    self._current_backoff = self.recovery_timeout
                    self._ring.clear()
            elif self.state == CircuitState.CLOSED:
                pass

    def record_failure(self) -> None:
        with self._lock:
            self._ring.append(1.0)
            if self.state == CircuitState.HALF_OPEN:
                self._half_open_probes_in_flight = max(0, self._half_open_probes_in_flight - 1)
                self._trip()
            elif self.state == CircuitState.CLOSED:
                error_rate = self._calculate_error_rate()
                if error_rate >= self.failure_rate_threshold:
                    self._trip()

    def _trip(self) -> None:
        self.state = CircuitState.OPEN
        backoff = self._current_backoff
        if self.jitter:
            backoff = backoff * (0.5 + random.random())
        self._next_attempt_time = time.time() + backoff
        self._current_backoff = min(self._current_backoff * self.backoff_multiplier, self.max_backoff)
        self._half_open_probes_in_flight = 0

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "error_rate": self._calculate_error_rate(),
                "next_attempt_time": self._next_attempt_time,
                "current_backoff": self._current_backoff,
            }

class CircuitBreakerMesh:
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_or_create(self, name: str, **kwargs: Any) -> CircuitBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name=name, **kwargs)
            return self._breakers[name]

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {name: cb.get_metrics() for name, cb in self._breakers.items()}

# Global circuit breaker mesh singleton
mesh = CircuitBreakerMesh()
