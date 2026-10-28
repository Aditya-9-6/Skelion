# gossipmesh_agent/key_pool.py
"""Thread‑safe API key pool for LLM providers.

The pool stores a list of API keys (or tokens) and provides the next available
key in a round‑robin fashion.  It integrates with Prometheus via the
``rate_limits_saved_total`` counter to record when a 429 response is observed
and the request is retried with the next key.

Usage example::

    from gossipmesh_agent.key_pool import KeyPool
    key_pool = KeyPool(["sk-...", "sk-..."], max_retries=3)
    key = key_pool.get_key()  # returns a key string
    # on 429 you can call ``key_pool.report_rate_limit()`` to rotate

The implementation is deliberately lightweight and has no external
dependencies beyond ``logging`` and ``prometheus_client`` (which is already a
runtime dependency of the project)."""

import logging
import itertools
import threading
from typing import List

from prometheus_client import Counter

logger = logging.getLogger(__name__)

# Prometheus counter for saved rate‑limit events (429 responses handled)
rate_limits_saved_total = Counter(
    "rate_limits_saved_total",
    "Number of times a 429 was handled by rotating to another API key",
)

class KeyPool:
    """Manage a rotating pool of API keys.

    Parameters
    ----------
    keys: List[str]
        List of API keys/tokens. The list must contain at least one entry.
    max_retries: int, optional
        Maximum number of rotation attempts before giving up. ``None`` means
        unlimited retries.
    """

    def __init__(self, keys: List[str], max_retries: int | None = None):
        if not keys:
            raise ValueError("KeyPool requires at least one API key.")
        self._keys = keys
        self._max_retries = max_retries
        self._lock = threading.Lock()
        # Cycle iterator provides round‑robin behaviour
        self._iterator = itertools.cycle(self._keys)
        # Track how many times each key was used (optional debugging)
        self._usage_counts = {k: 0 for k in self._keys}

    def get_key(self) -> str:
        """Return the next key from the pool in a thread‑safe manner."""
        with self._lock:
            key = next(self._iterator)
            self._usage_counts[key] += 1
            logger.debug("KeyPool selected key (usage %d): %s", self._usage_counts[key], key[:4] + "***")
            return key

    def report_rate_limit(self) -> None:
        """Record a 429 event and rotate to the next key.

        This method should be called by the caller when an LLM request returns
        HTTP 429. It increments the Prometheus counter and logs the rotation.
        """
        rate_limits_saved_total.inc()
        # The next call to ``get_key`` will automatically give the next key.
        logger.info("Rate limit encountered – rotating API key.")

    def get_usage_stats(self) -> dict:
        """Return a snapshot of key usage counts for monitoring/debugging."""
        with self._lock:
            return dict(self._usage_counts)

    def __repr__(self) -> str:
        return f"KeyPool(keys={len(self._keys)}, max_retries={self._max_retries})"
