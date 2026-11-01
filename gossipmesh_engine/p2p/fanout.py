import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FanoutMatrix:
    def record_ack(self, peer_id: str, success: bool) -> None:
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {}


class FanoutManager:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.matrix = FanoutMatrix()

    def compute_fanout(self) -> int:
        return 3

    def record_ack(self, peer_id: str, success: bool) -> None:
        self.matrix.record_ack(peer_id, success)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix.to_dict(),
        }
