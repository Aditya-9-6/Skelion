import math
import threading
import hashlib
from typing import List


class ProbabilisticFilterMesh:
    """
    Ephemeral, cache-conscious, bit-packed probabilistic filter mesh designed
    for low-memory anomaly deduplication and telemetry stream deduplication
    across high-throughput distributed agent nodes.

    Utilizes a packed bytearray vector with multiple hash functions mapped
    to bit offsets, supporting lock-free or fine-grained thread-safe updates.
    """

    def __init__(
        self, capacity: int = 100000, error_rate: float = 0.01, seed: int = 0x51E10
    ):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than 0.")
        if not (0.0 < error_rate < 1.0):
            raise ValueError("Error rate must be strictly between 0 and 1.")

        self.capacity = capacity
        self.error_rate = error_rate
        self.seed = seed

        # Optimal bit array size m = - (n * ln(p)) / (ln(2)^2)
        self.num_bits = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        # Align bits to full cache lines / bytes (64-byte chunks)
        self.num_bytes = math.ceil(self.num_bits / 8)
        # Pad to multiple of 64 bytes for cache-line alignment
        remainder = self.num_bytes % 64
        if remainder != 0:
            self.num_bytes += 64 - remainder
        self.num_bits = self.num_bytes * 8

        # Optimal number of hash functions k = (m / n) * ln(2)
        self.num_hashes = max(1, int((self.num_bits / capacity) * math.log(2)))

        self._bit_vector = bytearray(self.num_bytes)
        self._lock = threading.Lock()
        self._count = 0

    def _hashes(self, item: str) -> List[int]:
        """Generate k distinct bit positions using double hashing via SHA256 and SipHash/Murmur simulation."""
        encoded = item.encode("utf-8")
        digest = hashlib.sha256(encoded).digest()
        h1 = int.from_bytes(digest[:8], "big") ^ self.seed
        h2 = int.from_bytes(digest[8:16], "big") ^ ~self.seed

        positions = []
        num_bits = self.num_bits
        for i in range(self.num_hashes):
            pos = (h1 + i * h2) % num_bits
            positions.append(pos)
        return positions

    def add(self, item: str) -> None:
        """Add an item to the probabilistic filter atomically."""
        positions = self._hashes(item)
        with self._lock:
            for pos in positions:
                byte_idx = pos >> 3
                bit_offset = pos & 7
                self._bit_vector[byte_idx] |= 1 << bit_offset
            self._count += 1

    def __contains__(self, item: str) -> bool:
        return self.might_contain(item)

    def might_contain(self, item: str) -> bool:
        """Check if an item might be in the set. Returns False if definitely absent, True if probably present."""
        positions = self._hashes(item)
        # Read without heavy locking if possible, or lightweight lock for atomicity across bytes
        with self._lock:
            for pos in positions:
                byte_idx = pos >> 3
                bit_offset = pos & 7
                if not (self._bit_vector[byte_idx] & (1 << bit_offset)):
                    return False
        return True

    def clear(self) -> None:
        """Reset the filter vector and count."""
        with self._lock:
            for i in range(len(self._bit_vector)):
                self._bit_vector[i] = 0
            self._count = 0

    @property
    def fill_ratio(self) -> float:
        """Calculate current proportion of set bits in the bit vector."""
        with self._lock:
            set_bits = sum(bin(b).count("1") for b in self._bit_vector)
            return set_bits / self.num_bits
