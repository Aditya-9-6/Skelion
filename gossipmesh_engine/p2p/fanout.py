from typing import Dict, Any


class FanoutMatrix:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.matrix: Dict[str, bool] = {}

    def record_ack(self, peer_id: str, success: bool) -> None:
        self.matrix[peer_id] = success

    def compute_fanout(self) -> int:
        return len(self.matrix)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix,
        }

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix,
        }
