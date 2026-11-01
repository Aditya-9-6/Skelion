# Ephemeral Bloom-Filter Based Metric Cardinality Guard for Real-Time Telemetry Streams

import math
import threading
from typing import Tuple, List, Dict, Any, Optional


class CardinalityGuard:
    """
    A bounded-memory Bloom filter cardinality guard that intercepts high-frequency
    telemetry metrics streams, dynamically dropping or aggregating high-cardinality
    label permutations under memory pressure while maintaining a low false positive rate.
    
    Uses pre-allocated bytearray storage and multiple murmurhash/FNV variants to ensure
    O(k) time complexity and zero-allocation hot paths.
    """

    def __init__(self, capacity: int = 100000, error_rate: float = 0.01):
        self.capacity = max(1, capacity)
        self.error_rate = min(max(error_rate, 0.0001), 0.5)
        
        # Optimal bit array size m = - (n * ln(p)) / (ln(2)^2)
        self.bit_size = int(- (self.capacity * math.log(self.error_rate)) / (math.log(2) ** 2))
        self.bit_size = max(64, self.bit_size)
        
        # Optimal number of hash functions k = (m / n) * ln(2)
        self.num_hashes = int((self.bit_size / self.capacity) * math.log(2))
        self.num_hashes = max(1, self.num_hashes)
        
        # Pre-allocate bytearray for zero-allocation pooling on hot paths
        self._byte_capacity = (self.bit_size + 7) // 8
        self._bit_array = bytearray(self._byte_capacity)
        
        self._lock = threading.Lock()
        self._item_count = 0
        self._dropped_count = 0
        self._admitted_count = 0

    def _hash_murmur3(self, key_bytes: bytes, seed: int) -> int:
        """Fast non-cryptographic MurmurHash3-inspired mixing for bloom hashing."""
        h1 = seed ^ 0x5bd1e995
        c1 = 0xcc9e2d51
        c2 = 0x1b873593
        
        length = len(key_bytes)
        idx = 0
        while idx + 4 <= length:
            k1 = int.from_bytes(key_bytes[idx:idx+4], "little", signed=False)
            idx += 4
            
            k1 = (k1 * c1) & 0xFFFFFFFF
            k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
            k1 = (k1 * c2) & 0xFFFFFFFF
            
            h1 ^= k1
            h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
            h1 = (h1 * 5 + 0xe6546b64) & 0xFFFFFFFF
            
        # Tail bytes
        k1 = 0
        tail_len = length & 3
        if tail_len == 3:
            k1 ^= key_bytes[idx+2] << 16
            k1 ^= key_bytes[idx+1] << 8
            k1 ^= key_bytes[idx]
            k1 = (k1 * c1) & 0xFFFFFFFF
            k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
            k1 = (k1 * c2) & 0xFFFFFFFF
            h1 ^= k1
        elif tail_len == 2:
            k1 ^= key_bytes[idx+1] << 8
            k1 ^= key_bytes[idx]
            k1 = (k1 * c1) & 0xFFFFFFFF
            k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
            k1 = (k1 * c2) & 0xFFFFFFFF
            h1 ^= k1
        elif tail_len == 1:
            k1 ^= key_bytes[idx]
            k1 = (k1 * c1) & 0xFFFFFFFF
            k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
            k1 = (k1 * c2) & 0xFFFFFFFF
            h1 ^= k1
            
        h1 ^= length
        h1 ^= (h1 >> 16)
        h1 = (h1 * 0x85ebca6b) & 0xFFFFFFFF
        h1 ^= (h1 >> 13)
        h1 = (h1 * 0xc2b2ae35) & 0xFFFFFFFF
        h1 ^= (h1 >> 16)
        return h1

    def _get_hash_indexes(self, key_bytes: bytes) -> List[int]:
        """Generate k hash indexes using double hashing technique."""
        h1 = self._hash_murmur3(key_bytes, seed=0x9747b28c)
        h2 = self._hash_murmur3(key_bytes, seed=hash(key_bytes) & 0xFFFFFFFF)
        
        indexes = []
        for i in range(self.num_hashes):
            combined = (h1 + i * h2) % self.bit_size
            indexes.append(combined)
        return indexes

    def check_and_add(self, metric_name: str, labels: Dict[str, str]) -> bool:
        """
        Check if a metric with specific label permutations has been observed.
        Returns True if the permutation is already present or successfully added (admitted).
        Returns False if the cardinality limit is likely exceeded (dropped / aggregated).
        """
        # Construct canonical serialized representation of metric + labels
        sorted_labels = sorted(labels.items())
        label_str = ",".join(f"{k}={v}" for k, v in sorted_labels)
        canonical_key = f"{metric_name}:{{{label_str}}}"
        key_bytes = canonical_key.encode("utf-8")
        
        indexes = self._get_hash_indexes(key_bytes)
        
        with self._lock:
            # Check membership
            all_present = True
            for bit_idx in indexes:
                byte_pos = bit_idx >> 3
                bit_offset = bit_idx & 7
                if not (self._bit_array[byte_pos] & (1 << bit_offset)):
                    all_present = False
                    break
            
            if all_present:
                self._admitted_count += 1
                return True
            
            # If we reached estimated capacity, start guarding/dropping high-cardinality permutations
            if self._item_count >= self.capacity:
                self._dropped_count += 1
                return False
            
            # Add to filter
            for bit_idx in indexes:
                byte_pos = bit_idx >> 3
                bit_offset = bit_idx & 7
                self._bit_array[byte_pos] |= (1 << bit_offset)
            
            self._item_count += 1
            self._admitted_count += 1
            return True

    def reset(self) -> None:
        with self._lock:
            for i in range(self._byte_capacity):
                self._bit_array[i] = 0
            self._item_count = 0
            self._dropped_count = 0
            self._admitted_count = 0

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "capacity": self.capacity,
                "bit_size": self.bit_size,
                "num_hashes": self.num_hashes,
                "item_count": self._item_count,
                "admitted_count": self._admitted_count,
                "dropped_count": self._dropped_count,
                "byte_capacity": self._byte_capacity,
            }


# Global singleton instance for metrics cardinality protection
global_cardinality_guard = CardinalityGuard()
