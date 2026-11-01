import hashlib
import threading
from typing import List, Optional, Tuple


def calculate_xor_distance(id1: str, id2: str) -> int:
    val1 = (
        int(id1, 16)
        if all(c in "0123456789abcdefABCDEF" for c in id1)
        else int(hashlib.sha256(id1.encode()).hexdigest(), 16)
    )
    val2 = (
        int(id2, 16)
        if all(c in "0123456789abcdefABCDEF" for c in id2)
        else int(hashlib.sha256(id2.encode()).hexdigest(), 16)
    )
    return val1 ^ val2


class KademliaBucket:
    def __init__(self, k: int = 20) -> None:
        self.k = k
        self.nodes: List[Tuple[str, str]] = []
        self._lock = threading.Lock()

    def add_node(self, peer_id: str, address: str) -> bool:
        with self._lock:
            for i, (p_id, _) in enumerate(self.nodes):
                if p_id == peer_id:
                    self.nodes.pop(i)
                    self.nodes.append((peer_id, address))
                    return True
            if len(self.nodes) < self.k:
                self.nodes.append((peer_id, address))
                return True
            else:
                return False

    def get_nodes(self) -> List[Tuple[str, str]]:
        with self._lock:
            return list(self.nodes)


class KademliaDHT:
    def __init__(self, node_id: Optional[str] = None, k: int = 20) -> None:
        self.node_id = (
            node_id or hashlib.sha256(str(threading.get_ident()).encode()).hexdigest()
        )
        self.k = k
        self.buckets = [KademliaBucket(k=k)]
        self._lock = threading.Lock()

    def add_peer(self, peer_id: str, address: str) -> bool:
        with self._lock:
            return self.buckets[0].add_node(peer_id, address)

    def find_close_nodes(self, target_id: str, count: int = 5) -> List[Tuple[str, str]]:
        with self._lock:
            all_nodes: List[Tuple[str, str]] = []
            for bucket in self.buckets:
                all_nodes.extend(bucket.get_nodes())

            all_nodes.sort(key=lambda item: calculate_xor_distance(item[0], target_id))
            return all_nodes[:count]
