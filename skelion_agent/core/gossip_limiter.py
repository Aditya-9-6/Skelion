import time
import threading
from typing import Dict, Tuple, Optional, Any
from gossipmesh_engine.core.clocks import VectorClock
from gossipmesh_engine.core.exceptions import GossipMeshException

class RateLimitExceededError(GossipMeshException):
    def __init__(self, message: str = "Rate limit exceeded via gossip mesh", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED", details=details)


class GossipTokenBucket:
    """
    Thread-safe token bucket state representing capacity and refill metrics
    for a given identifier and rate limit policy.
    """
    def __init__(self, capacity: float, refill_rate: float, initial_tokens: Optional[float] = None):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)  # tokens per second
        self.tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> Tuple[bool, float, float]:
        """
        Consumes tokens atomically from the local bucket.
        Returns: (is_allowed, remaining_tokens, reset_time_seconds)
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            if elapsed > 0:
                refilled = elapsed * self.refill_rate
                self.tokens = min(self.capacity, self.tokens + refilled)
                self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                allowed = True
            else:
                allowed = False

            remaining = self.tokens
            # Calculate reset time if bucket is not full
            deficit = self.capacity - self.tokens
            reset_in = (deficit / self.refill_rate) if self.refill_rate > 0 else 0.0
            reset_time = time.time() + reset_in
            return allowed, remaining, reset_time

    def merge(self, remote_tokens: float, remote_last_refill: float) -> None:
        """
        Merges remote token state using convergence heuristics (e.g., most recent update).
        """
        with self._lock:
            now = time.monotonic()
            if remote_last_refill >= self.last_refill:
                self.tokens = min(self.capacity, float(remote_tokens))
                self.last_refill = now


class GossipRateLimiter:
    """
    Distributed, lock-free token bucket rate limiter synchronized via epidemic gossip.
    """
    def __init__(self, node_id: str, capacity: float, refill_rate: float):
        self.node_id = node_id
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: Dict[str, GossipTokenBucket] = {}
        self.vector_clock = VectorClock(node_id)
        self._global_lock = threading.Lock()

    def _get_bucket(self, identifier: str) -> GossipTokenBucket:
        with self._global_lock:
            if identifier not in self._buckets:
                self._buckets[identifier] = GossipTokenBucket(self.capacity, self.refill_rate)
            return self._buckets[identifier]

    def check_and_consume(self, identifier: str, tokens: float = 1.0) -> Tuple[bool, float, float]:
        """
        Evaluates rate limits locally with sub-microsecond atomic operations.
        Returns: (is_allowed, remaining_tokens, reset_time)
        """
        bucket = self._get_bucket(identifier)
        allowed, remaining, reset_time = bucket.consume(tokens)
        self.vector_clock.increment()
        return allowed, remaining, reset_time

    def enforce(self, identifier: str, tokens: float = 1.0) -> Tuple[float, float]:
        allowed, remaining, reset_time = self.check_and_consume(identifier, tokens)
        if not allowed:
            raise RateLimitExceededError(details={
                "capacity": self.capacity,
                "remaining": remaining,
                "reset": reset_time,
                "node_id": self.node_id
            })
        return remaining, reset_time

    def get_gossip_state(self, identifier: str) -> Dict[str, Any]:
        """
        Generates a state payload including vector clock delta for epidemic dissemination.
        """
        bucket = self._get_bucket(identifier)
        with bucket._lock:
            tokens = bucket.tokens
            last_refill = bucket.last_refill

        return {
            "identifier": identifier,
            "tokens": tokens,
            "last_refill": last_refill,
            "vector_clock": self.vector_clock.snapshot(),
            "node_id": self.node_id
        }

    def receive_gossip(self, state: Dict[str, Any]) -> None:
        """
        Reconciles incoming gossip state from a peer node using vector clocks and token merging.
        """
        identifier = state.get("identifier")
        remote_clock = state.get("vector_clock", {})
        remote_tokens = state.get("tokens", self.capacity)
        remote_refill = state.get("last_refill", time.monotonic())

        if not identifier:
            return

        # Update vector clock
        self.vector_clock.update(remote_clock)

        # Merge token bucket state
        bucket = self._get_bucket(identifier)
        bucket.merge(remote_tokens, remote_refill)
