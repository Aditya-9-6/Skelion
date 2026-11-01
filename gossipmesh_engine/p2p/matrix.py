import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ReachabilityMatrix:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.reachability: Dict[str, float] = {}

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
