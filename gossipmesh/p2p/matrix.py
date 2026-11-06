from typing import Any, Dict


class ReachabilityMatrix:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.reachability: Dict[str, float] = {}

    def average_reachability(self) -> float:
        if not self.reachability:
            return 0.0
        return sum(self.reachability.values()) / len(self.reachability)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "reachability": self.reachability,
            "average": self.average_reachability(),
        }
