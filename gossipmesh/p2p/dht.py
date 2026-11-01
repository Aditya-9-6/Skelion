import hashlib
import threading
from typing import Dict, List, Optional, Tuple


class KademliaNode:
    def __init__(self, peer_id: str, address: str) -> None:
        self.peer_id = peer_id
        self.address = address
        self.digest = self._hash_id(peer_id)

    @staticmethod
    def _hash_id(peer_id: str) -> int:
        return int(hashlib.sha1(peer_id.encode("utf-8")).hexdigest(), 16)

    def xor_distance(self, other_digest: int) -> int:
        return self.digest ^ other_digest


class KademliaBucket:
    def __init__(self, k_size: int = 20) -> None:
        self.k_size = k_size
        self.nodes: List[KademliaNode] = []
        self._lock = threading.Lock()

    def update(self, node: KademliaNode) -> None:
        with self._lock:
            for i, existing in enumerate(self.nodes):
                if existing.peer_id == node.peer_id:
                    self.nodes.pop(i)
                    self.nodes.append(node)
                    return
            if len(self.nodes) < self.k_size:
                self.nodes.append(node)
            else:
                # Bucket is full; in standard Kademlia we ping the tail node.
                # Here we implement a simple replacement/drop policy.
                pass

    def remove(self, peer_id: str) -> None:
        with self._lock:
            self.nodes = [n for n in self.nodes if n.peer_id != peer_id]

    def get_nodes(self) -> List[KademliaNode]:
        with self._lock:
            return list(self.nodes)


class KademliaDHT:
    def __init__(self, local_peer_id: str, local_address: str, k_size: int = 20, b_bits: int = 160) -> None:
        self.local_node = KademliaNode(local_peer_id, local_address)
        self.k_size = k_size
        self.b_bits = b_bits
        self.buckets: List[KademliaBucket] = [KademliaBucket(k_size) for _ in range(b_bits)]
        self._lock = threading.Lock()

    def _bucket_index(self, distance: int) -> int:
        if distance == 0:
            return 0
        # Find the index of the highest bit set
        bit_len = distance.bit_length()
        idx = self.b_bits - bit_len
        return max(0, min(idx, self.b_bits - 1))

    def add_node(self, peer_id: str, address: str) -> None:
        node = KademliaNode(peer_id, address)
        if node.peer_id == self.local_node.peer_id:
            return
        distance = self.local_node.xor_distance(node.digest)
        b_idx = self._bucket_index(distance)
        with self._lock:
            self.buckets[b_idx].update(node)

    def remove_node(self, peer_id: str) -> None:
        digest = KademliaNode._hash_id(peer_id)
        distance = self.local_node.xor_distance(digest)
        b_idx = self._bucket_index(distance)
        with self._lock:
            self.buckets[b_idx].remove(peer_id)

    def find_closest_nodes(self, target_peer_id: str, count: int = 5) -> List[KademliaNode]:
        target_digest = KademliaNode._hash_id(target_peer_id)
        with self._lock:
            all_nodes = []
            for bucket in self.buckets:
                all_nodes.extend(bucket.get_nodes())
        
        # Sort by XOR distance to target digest
        all_nodes.sort(key=lambda n: n.xor_distance(target_digest))
        return all_nodes[:count]
