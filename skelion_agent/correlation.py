import threading
import hashlib
from typing import List, Dict, Any, Optional


class CountMinSketch:
    """Space-efficient frequency sketch backbone for telemetry pruning."""
    def __init__(self, width: int = 2048, depth: int = 4) -> None:
        self.width = width
        self.depth = depth
        self.table = [[0] * width for _ in range(depth)]
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> List[int]:
        hashes = []
        for i in range(self.depth):
            h = hashlib.blake2b(item.encode('utf-8'), digest_size=8, person=bytes([i]))
            hashes.append(int.from_bytes(h.digest(), 'big') % self.width)
        return hashes

    def add(self, item: str, count: int = 1) -> None:
        with self._lock:
            for i, idx in enumerate(self._hashes(item)):
                self.table[i][idx] += count

    def estimate(self, item: str) -> int:
        with self._lock:
            return min(self.table[i][idx] for i, idx in enumerate(self._hashes(item)))


class TrieNode:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.children: Dict[str, 'TrieNode'] = {}
        self.incident_count = 0
        self.metadata: List[Dict[str, Any]] = []
        self._lock = threading.Lock()


class IncidentCorrelationEngine:
    """Bounded-Memory Prefix-Tree Incident Root-Cause Correlation Engine."""
    def __init__(self, max_nodes: int = 50000, sketch_width: int = 2048, sketch_depth: int = 4) -> None:
        self.root = TrieNode()
        self.max_nodes = max_nodes
        self.node_count = 1
        self.sketch = CountMinSketch(width=sketch_width, depth=sketch_depth)
        self._lock = threading.Lock()

    def insert_path(self, path_segments: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        if not path_segments:
            return

        path_key = ":".join(path_segments)
        self.sketch.add(path_key, 1)

        with self._lock:
            current = self.root
            for segment in path_segments:
                with current._lock:
                    if segment not in current.children:
                        if self.node_count >= self.max_nodes:
                            # Bounded memory enforcement: prune or bypass lowest frequency nodes
                            # For high throughput, we skip insertion if max capacity is breached
                            return
                        current.children[segment] = TrieNode(name=segment)
                        self.node_count += 1
                    current = current.children[segment]

            with current._lock:
                current.incident_count += 1
                if metadata:
                    current.metadata.append(metadata)

    def correlate(self, path_prefix: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        with self._lock:
            current = self.root
            for segment in path_prefix:
                if segment not in current.children:
                    return []
                current = current.children[segment]

            # Traverse and gather descending patterns
            results = []
            stack = [current]
            while stack:
                node = stack.pop()
                if node.incident_count > 0:
                    results.append({
                        "name": node.name,
                        "incident_count": node.incident_count,
                        "frequency_estimate": self.sketch.estimate(node.name),
                        "metadata": node.metadata
                    })
                for child in node.children.values():
                    stack.append(child)

            results.sort(key=lambda x: x["incident_count"], reverse=True)
            return results[:top_k]
