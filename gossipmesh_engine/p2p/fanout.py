from typing import Any, Dict


class FanoutMatrix:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.matrix: Any = None

    def compute_fanout(self) -> int:
        return 10

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
        }
