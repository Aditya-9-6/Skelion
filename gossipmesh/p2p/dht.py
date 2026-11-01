import hashlib
import threading
from typing import List, Optional, Tuple


def calculate_xor_distance(id1: str, id2: str) -> int:
    val1 = (
        int(id1, 16)
        if len(id1) == 64
        else int(hashlib.sha256(id1.encode()).hexdigest(), 16)
    )
    val2 = (
        int(id2, 16)
        if len(id2) == 64
        else int(hashlib.sha256(id2.encode()).hexdigest(), 16)
    )
    return val1 ^ val2


class KademliaBucket:
    def __init__(self, k: int = 20):
        self.k = k
        self.nodes: List[Tuple[str, str]] = []  # List of (node_id, address)

    def add_node(self, node_id: str, address: str) -> bool:
        for i, (nid, addr) in enumerate(self.nodes):
            if nid == node_id:
                self.nodes[i] = (node_id, address)
                return True
        if len(self.nodes) < self.k:
            self.nodes.append((node_id, address))
            return True
        else:
            # Bucket is full; implement LRU eviction check
            return False

    def remove_node(self, node_id: str) -> None:
        self.nodes = [n for n in self.nodes if n[0] != node_id]

    def get_nodes(self) -> List[Tuple[str, str]]:
        return list(self.nodes)


class KademliaDHT:
    def __init__(self, node_id: Optional[str] = None, k: int = 20):
        self.node_id = (
            node_id
            or hashlib.sha256(threading.current_thread().name.encode()).hexdigest()
        )
        self.k = k
        self.buckets: List[KademliaBucket] = [KademliaBucket(k=k)]
        self._lock = threading.Lock()

    def _get_bucket(self, peer_id: str) -> KademliaBucket:
        return self.buckets[0]

    def add_peer(self, peer_id: str, address: str) -> bool:
        with self._lock:
            bucket = self._get_bucket(peer_id)
            return bucket.add_node(peer_id, address)

    def remove_peer(self, peer_id: str) -> None:
        with self._lock:
            bucket = self._get_bucket(peer_id)
            bucket.remove_node(peer_id)

    def find_close_nodes(
        self, target_id: str, count: int = 20
    ) -> List[Tuple[str, str]]:
        with self._lock:
            all_nodes: List[Tuple[str, str]] = []
            for bucket in self.buckets:
                all_nodes.extend(bucket.get_nodes())

            all_nodes.sort(key=lambda item: calculate_xor_distance(item[0], target_id))
            return all_nodes[:count]
