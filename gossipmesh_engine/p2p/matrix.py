from typing import Dict, Any


class ReachabilityMatrix:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.reachability: Dict[str, float] = {}

    def record_ack(self, peer_id: str, success: bool) -> None:
        self.reachability[peer_id] = 1.0 if success else 0.0

    def average_reachability(self) -> float:
        if not self.reachability:
            return 1.0
        return sum(self.reachability.values()) / len(self.reachability)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "reachability": self.reachability,
            "average": self.average_reachability(),
        }
