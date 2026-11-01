from typing import Any, Dict


class FanoutManager:
    def __init__(self, node_id: str, matrix: Any) -> None:
        self.node_id = node_id
        self.matrix = matrix

    def record_ack(self, peer_id: str, success: bool) -> None:
        self.matrix.record_ack(peer_id, success)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix.to_dict(),
        }

    def compute_fanout(self) -> int:
        return 8
