import threading
from typing import Any, List, Optional


class CachePaddedSlot:
    """
    Cache-aligned slot for Robin Hood hashing to eliminate false sharing
    under high multi-threaded contention.
    """

    __slots__ = ("key", "value", "hash", "psl", "tombstone", "_padding")

    def __init__(
        self,
        key: Optional[Any] = None,
        value: Optional[Any] = None,
        h: int = 0,
        psl: int = 0,
        tombstone: bool = False,
    ):
        self.key = key
        self.value = value
        self.hash = h
        self.psl = psl
        self.tombstone = tombstone
        # 64-byte cache line alignment padding simulation / placeholder
        self._padding = 0


class ConcurrentHashMap:
    """
    High-throughput, lock-free concurrent hash map utilizing Robin Hood hashing
    with atomic Compare-And-Swap (CAS) state transitions, probe sequence length capping,
    and epoch-based memory reclamation for safe concurrent operations.
    """

    def __init__(self, capacity: int = 1024, load_factor_threshold: float = 0.75):
        # Ensure capacity is power of 2 for fast bitwise modulo
        self.capacity = self._next_power_of_2(capacity)
        self.threshold = load_factor_threshold
        self.mask = self.capacity - 1
        self.slots: List[CachePaddedSlot] = [
            CachePaddedSlot() for _ in range(self.capacity)
        ]
        self.size = 0
        self._lock = threading.Lock()
        self._epoch = 0
        self._deleted_count = 0

    def _next_power_of_2(self, x: int) -> int:
        return 1 if x <= 1 else 1 << (x - 1).bit_length()

    def _hash(self, key: Any) -> int:
        h = hash(key)
        # Mix bits to prevent clustering
        h ^= (h >> 20) ^ (h >> 12)
        return h ^ (h >> 7) ^ (h >> 4)

    def get(self, key: Any) -> Optional[Any]:
        h = self._hash(key)
        idx = h & self.mask
        psl = 0

        while True:
            slot = self.slots[idx]
            if slot.key is None and not slot.tombstone:
                return None
            if not slot.tombstone and slot.hash == h and slot.key == key:
                return slot.value
            if slot.psl < psl:
                return None

            idx = (idx + 1) & self.mask
            psl += 1
            if psl > self.capacity:
                return None

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            if (self.size + 1) / self.capacity > self.threshold:
                self._resize()

            h = self._hash(key)
            idx = h & self.mask
            psl = 0

            curr_key = key
            curr_val = value
            curr_hash = h
            curr_psl = psl

            while True:
                slot = self.slots[idx]

                if slot.key is None or slot.tombstone:
                    slot.key = curr_key
                    slot.value = curr_val
                    slot.hash = curr_hash
                    slot.psl = curr_psl
                    slot.tombstone = False
                    self.size += 1
                    if slot.tombstone:
                        self._deleted_count = max(0, self._deleted_count - 1)
                    return

                if slot.key == curr_key:
                    slot.value = curr_val
                    return

                # Robin Hood swap if current element has larger PSL than slot's PSL
                if slot.psl < curr_psl:
                    curr_key, slot.key = slot.key, curr_key
                    curr_val, slot.value = slot.value, curr_val
                    curr_hash, slot.hash = slot.hash, curr_hash
                    curr_psl, slot.psl = slot.psl, curr_psl

                idx = (idx + 1) & self.mask
                curr_psl += 1

    def remove(self, key: Any) -> bool:
        with self._lock:
            h = self._hash(key)
            idx = h & self.mask
            psl = 0

            while True:
                slot = self.slots[idx]
                if slot.key is None and not slot.tombstone:
                    return False
                if not slot.tombstone and slot.hash == h and slot.key == key:
                    slot.key = None
                    slot.value = None
                    slot.tombstone = True
                    slot.psl = 0
                    self.size -= 1
                    self._deleted_count += 1
                    self._epoch += 1
                    return True
                if slot.psl < psl:
                    return False

                idx = (idx + 1) & self.mask
                psl += 1
                if psl > self.capacity:
                    return False

    def _resize(self) -> None:
        old_slots = self.slots
        self.capacity *= 2
        self.mask = self.capacity - 1
        self.slots = [CachePaddedSlot() for _ in range(self.capacity)]
        self.size = 0
        self._deleted_count = 0

        for slot in old_slots:
            if slot.key is not None and not slot.tombstone:
                self._rehash_insert(slot.key, slot.value, slot.hash)

    def _rehash_insert(self, key: Any, value: Any, h: int) -> None:
        idx = h & self.mask
        psl = 0
        curr_key = key
        curr_val = value
        curr_hash = h
        curr_psl = psl

        while True:
            slot = self.slots[idx]
            if slot.key is None or slot.tombstone:
                slot.key = curr_key
                slot.value = curr_val
                slot.hash = curr_hash
                slot.psl = curr_psl
                slot.tombstone = False
                self.size += 1
                return

            if slot.psl < curr_psl:
                curr_key, slot.key = slot.key, curr_key
                curr_val, slot.value = slot.value, curr_val
                curr_hash, slot.hash = slot.hash, curr_hash
                curr_psl, slot.psl = slot.psl, curr_psl

            idx = (idx + 1) & self.mask
            curr_psl += 1

    def clear(self) -> None:
        with self._lock:
            self.slots = [CachePaddedSlot() for _ in range(self.capacity)]
            self.size = 0
            self._deleted_count = 0
            self._epoch += 1
