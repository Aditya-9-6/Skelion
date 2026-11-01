import heapq
from typing import Dict, List, Tuple, Any, Optional


class HeavyHitters:
    """
    Space-Saving streaming heavy hitters algorithm implementation.
    Provides O(1/epsilon) memory bounds for identifying high-frequency items in
    massive real-time telemetry streams.
    """

    def __init__(self, capacity: int = 100):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than 0")
        self.capacity = capacity
        self.counters: Dict[Any, int] = {}
        self.errors: Dict[Any, int] = {}
        self._min_heap: List[Tuple[int, Any]] = []
        self._item_to_heap_node: Dict[Any, Tuple[int, Any]] = {}
        self._total_count = 0

    def add(self, item: Any, count: int = 1) -> None:
        if count <= 0:
            return
        self._total_count += count

        if item in self.counters:
            self.counters[item] += count
            # Update min-heap efficiently
            self._update_heap(item)
        elif len(self.counters) < self.capacity:
            self.counters[item] = count
            self.errors[item] = 0
            node = (count, item)
            heapq.heappush(self._min_heap, node)
            self._item_to_heap_node[item] = node
        else:
            # Evict minimum element and replace with new item
            min_count, min_item = self._get_min_item()
            if min_item is not None:
                del self.counters[min_item]
                del self.errors[min_item]
                self._item_to_heap_node.pop(min_item, None)

            self.counters[item] = min_count + count
            self.errors[item] = min_count

            node = (min_count + count, item)
            heapq.heappush(self._min_heap, node)
            self._item_to_heap_node[item] = node

            # Clean up stale heap elements lazily or explicitly
            self._cleanup_heap()

    def _update_heap(self, item: Any):
        # Lazy update or rebuild/push new node
        new_count = self.counters[item]
        old_node = self._item_to_heap_node.get(item)
        if old_node:
            # Since python's heapq doesn't support decrease_key directly without rebuilding or marking invalid,
            # we push the new node and filter stale nodes during min extraction.
            new_node = (new_count, item)
            heapq.heappush(self._min_heap, new_node)
            self._item_to_heap_node[item] = new_node

    def _get_min_item(self) -> Tuple[int, Any]:
        while self._min_heap:
            count, item = self._min_heap[0]
            if item in self.counters and self.counters[item] == count:
                return count, item
            heapq.heappop(self._min_heap)
        return 0, None

    def _cleanup_heap(self):
        # Keep heap size proportional to capacity to prevent unbounded memory growth from stale entries
        if len(self._min_heap) > 2 * self.capacity:
            self._min_heap = [(self.counters[item], item) for item in self.counters]
            heapq.heapify(self._min_heap)
            self._item_to_heap_node = {
                item: (self.counters[item], item) for item in self.counters
            }

    def get_heavy_hitters(
        self, threshold_fraction: float = 0.01
    ) -> List[Tuple[Any, int, int]]:
        """
        Returns items whose frequency exceeds threshold_fraction * total_count.
        Returns a list of tuples: (item, estimated_count, max_error).
        """
        threshold = threshold_fraction * self._total_count
        result = []
        for item, count in self.counters.items():
            if count >= threshold:
                error = self.errors.get(item, 0)
                result.append((item, count, error))
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def query(self, item: Any) -> Tuple[Optional[int], int]:
        """
        Query an item's estimated frequency and maximum possible error.
        Returns (estimated_count, error) or (None, 0) if not tracked.
        """
        if item in self.counters:
            return self.counters[item], self.errors.get(item, 0)
        return None, 0

    def reset(self) -> None:
        self.counters.clear()
        self.errors.clear()
        self._min_heap.clear()
        self._item_to_heap_node.clear()
        self._total_count = 0
