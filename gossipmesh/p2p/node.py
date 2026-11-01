import time
import threading
from typing import Dict, Any, Optional, List
from gossipmesh.p2p.health import SlidingWindowPeerHealthScorecard, PeerHealthConfig
from gossipmesh.p2p.dht import KademliaDHT, KademliaNode


class P2PNode:
    def __init__(
        self,
        peer_id: str,
        address: str,
        health_config: Optional[PeerHealthConfig] = None,
    ) -> None:
        self.peer_id = peer_id
        self.address = address
        self.scorecard = SlidingWindowPeerHealthScorecard(health_config)
        self.connected_at = time.time()
        self.dht = KademliaDHT(peer_id, address)
        self._lock = threading.Lock()

    def record_interaction(
        self, latency_ms: float, dropped: bool = False, violated: bool = False
    ) -> float:
        return self.scorecard.record_sample(latency_ms, dropped, violated)

    def is_healthy(self) -> bool:
        metrics = self.scorecard.get_metrics()
        return not metrics["is_quarantined"]

    def register_peer(self, peer_id: str, address: str) -> None:
        with self._lock:
            self.dht.add_node(peer_id, address)

    def unregister_peer(self, peer_id: str) -> None:
        with self._lock:
            self.dht.remove_node(peer_id)

    def find_peers(self, target_peer_id: str, count: int = 5) -> List[KademliaNode]:
        with self._lock:
            return self.dht.find_closest_nodes(target_peer_id, count)

    def get_status(self) -> Dict[str, Any]:
        metrics = self.scorecard.get_metrics()
        with self._lock:
            total_known_peers = sum(len(b.get_nodes()) for b in self.dht.buckets)
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "connected_at": self.connected_at,
            "known_dht_peers": total_known_peers,
            **metrics,
        }
