import hashlib
import threading
from typing import List, Dict, Tuple, Optional


def calculate_distance(node_id_1: str, node_id_2: str) -> int:
    """Calculates the XOR distance between two hex-encoded node IDs."""
    b1 = bytes.fromhex(node_id_1)
    b2 = bytes.fromhex(node_id_2)
    val1 = int.from_bytes(b1, "big")
    val2 = int.from_bytes(b2, "big")
    return val1 ^ val2


class KademliaBucket:
    def __init__(self, k_size: int = 20) -> None:
        self.k_size = k_size
        self.nodes: List[Tuple[str, str]] = []  # List of (node_id, address)
        self._lock = threading.Lock()

    def add_node(self, node_id: str, address: str) -> bool:
        with self._lock:
            for i, (nid, addr) in enumerate(self.nodes):
                if nid == node_id:
                    # Refresh node by moving it to the tail (most recently seen)
                    self.nodes.pop(i)
                    self.nodes.append((node_id, address))
                    return True
            
            if len(self.nodes) < self.k_size:
                self.nodes.append((node_id, address))
                return True
            
            # Bucket is full; in strict Kademlia we ping the head, here we drop or keep
            return False

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            self.nodes = [(nid, addr) for nid, addr in self.nodes if nid != node_id]

    def get_nodes(self) -> List[Tuple[str, str]]:
        with self._lock:
            return list(self.nodes)


class KademliaDHT:
    def __init__(self, local_node_id: str, k_size: int = 20) -> None:
        self.local_node_id = local_node_id
        self.k_size = k_size
        # 160 bits for SHA-1 based IDs, or standard 256 bits (64 hex chars)
        self.buckets: List[KademliaBucket] = [KademliaBucket(k_size) for _ in range(256)]
        self._lock = threading.Lock()

    def _bucket_index(self, node_id: str) -> int:
        dist = calculate_distance(self.local_node_id, node_id)
        if dist == 0:
            return 0
        # Find the highest bit set
        return dist.bit_length() - 1

    def add_node(self, node_id: str, address: str) -> bool:
        if node_id == self.local_node_id:
            return False
        idx = self._bucket_index(node_id)
        if idx >= len(self.buckets):
            idx = len(self.buckets) - 1
        return self.buckets[idx].add_node(node_id, address)

    def remove_node(self, node_id: str) -> None:
        idx = self._bucket_index(node_id)
        if idx < len(self.buckets):
            self.buckets[idx].remove_node(node_id)

    def find_closest_nodes(self, target_node_id: str, count: int = 20) -> List[Tuple[str, str]]:
        with self._lock:
            all_nodes: List[Tuple[str, str]] = []
            for bucket in self.buckets:
                all_nodes.extend(bucket.get_nodes())
            
            # Sort by XOR distance to target_node_id
            all_nodes.sort(key=lambda item: calculate_distance(item[0], target_node_id))
            return all_nodes[:count]


def generate_node_id(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()
