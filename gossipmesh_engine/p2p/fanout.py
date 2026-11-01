from typing import Dict, Any


class FanoutManager:
    def __init__(self, node_id: str, matrix: Any):
        self.node_id = node_id
        self.matrix = matrix

    def record_ack(self, peer_id: str, success: bool) -> None:
        self.matrix.record_ack(peer_id, success)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": 5,
            "matrix": self.matrix.to_dict(),
        }
