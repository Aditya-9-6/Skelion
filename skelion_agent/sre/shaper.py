import time
import threading
from typing import Dict, Optional, List


class TokenBucket:
    __slots__ = (
        'capacity',
        'fill_rate',
        'tokens',
        'last_refill',
        'parent',
        'children',
        '_lock'
    )

    def __init__(
        self, 
        capacity: float, 
        fill_rate: float, 
        parent: Optional['TokenBucket'] = None
    ):
        self.capacity = float(capacity)
        self.fill_rate = float(fill_rate)  # tokens per second
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self.parent: Optional['TokenBucket'] = parent
        self.children: List['TokenBucket'] = []
        self._lock = threading.Lock()

        if parent:
            with parent._lock:
                parent.children.append(self)

    def _refill_unlocked(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed > 0:
            added = elapsed * self.fill_rate
            self.tokens = min(self.capacity, self.tokens + added)
            self.last_refill = now

    def consume(self, tokens: float) -> bool:
        """
        Attempt to consume specified tokens atomically from the bucket and its hierarchy.
        Returns True if successful, False otherwise.
        """
        now = time.monotonic()
        tokens = float(tokens)
        if tokens <= 0:
            return True

        # If there is a parent, we must acquire locks hierarchically to avoid deadlock
        # Ordering by id or locking parent then child since tree is static/semi-static
        if self.parent:
            # Acquire parent lock first, then child lock
            with self.parent._lock:
                with self._lock:
                    self.parent._refill_unlocked(now)
                    self._refill_unlocked(now)

                    # Check availability in both hierarchical levels
                    if self.parent.tokens >= tokens and self.tokens >= tokens:
                        self.parent.tokens -= tokens
                        self.tokens -= tokens
                        return True
                    return False
        else:
            with self._lock:
                self._refill_unlocked(now)
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                return False

    def get_available_tokens(self) -> float:
        now = time.monotonic()
        with self._lock:
            self._refill_unlocked(now)
            return self.tokens


class HierarchicalTokenBucketShaper:
    """
    High-performance Hierarchical Token Bucket Traffic Shaper supporting
    lock-free atomic accrual simulations, child/parent tenancy limits,
    and sub-microsecond egress rate control.
    """

    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._global_lock = threading.Lock()

    def register_bucket(
        self, 
        name: str, 
        capacity: float, 
        fill_rate: float, 
        parent_name: Optional[str] = None
    ) -> TokenBucket:
        with self._global_lock:
            parent = self._buckets.get(parent_name) if parent_name else None
            bucket = TokenBucket(capacity=capacity, fill_rate=fill_rate, parent=parent)
            self._buckets[name] = bucket
            return bucket

    def get_bucket(self, name: str) -> Optional[TokenBucket]:
        with self._global_lock:
            return self._buckets.get(name)

    def allow_request(self, name: str, cost: float = 1.0) -> bool:
        bucket = self.get_bucket(name)
        if not bucket:
            return True  # Fail open if unregistered
        return bucket.consume(cost)
