import hashlib
import threading
from typing import Dict, List, Optional, Tuple


def calculate_xor_distance(id1: str, id2: str) -> int:
    """Calculate the XOR distance between two hex-encoded node IDs."""
    val1 = int(id1, 16)
    val2 = int(id2, 16)
    return val1 ^ val2


class KademliaBucket:
    def __init__(self, prefix: str, k: int = 20) -> None:
        self.prefix = prefix
        self.k = k
        self.nodes: List[Tuple[str, str]] = []  # List of (peer_id, address)
        self._lock = threading.Lock()

    def add_node(self, peer_id: str, address: str) -> bool:
        with self._lock:
            for i, (pid, addr) in enumerate(self.nodes):
                if pid == peer_id:
                    # Refresh node to tail (most recently seen)
                    self.nodes.pop(i)
                    self.nodes.append((peer_id, address))
                    return True
            if len(self.nodes) < self.k:
                self.nodes.append((peer_id, address))
                return True
            return False

    def remove_node(self, peer_id: str) -> None:
        with self._lock:
            self.nodes = [(pid, addr) for pid, addr in self.nodes if pid != peer_id]

    def get_nodes(self) -> List[Tuple[str, str]]:
        with self._lock:
            return list(self.nodes)


class KademliaDHT:
    def __init__(self, node_id: Optional[str] = None, k: int = 20) -> None:
        self.node_id = node_id or hashlib.sha256(b"default_node").hexdigest()
        self.k = k
        self.buckets: List[KademliaBucket] = [KademliaBucket("", k=k)]
        self._lock = threading.Lock()

    def _get_bucket(self, peer_id: str) -> KademliaBucket:
        dist = calculate_xor_distance(self.node_id, peer_id)
        # For simplicity in a flat single bucket or basic routing table:
        return self.buckets[0]

    def add_peer(self, peer_id: str, address: str) -> bool:
        with self._lock:
            bucket = self._get_bucket(peer_id)
            return bucket.add_node(peer_id, address)

    def remove_peer(self, peer_id: str) -> None:
        with self._lock:
            bucket = self._get_bucket(peer_id)
            bucket.remove_node(peer_id)

    def find_close_nodes(self, target_id: str, count: int = 5) -> List[Tuple[str, str]]:
        with self._lock:
            all_nodes: List[Tuple[str, str]] = []
            for bucket in self.buckets:
                all_nodes.extend(bucket.get_nodes())
            
            # Sort by XOR distance to target_id
            all_nodes.sort(key=lambda item: calculate_xor_distance(item[0], target_id))
            return all_nodes[:count]
