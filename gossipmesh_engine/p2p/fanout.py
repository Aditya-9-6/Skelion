from typing import Dict, Any


class FanoutManager:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.matrix = type(
            "MockMatrix",
            (),
            {"record_ack": lambda self, p, s: None, "to_dict": lambda self: {}},
        )()

    def compute_fanout(self) -> int:
        return 5

    def record_ack(self, peer_id: str, success: bool) -> None:
        self.matrix.record_ack(peer_id, success)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix.to_dict(),
        }
