from typing import Dict, Any


class EpidemicFanout:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.matrix: Any = None

    def compute_fanout(self) -> int:
        return 3

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": getattr(self.matrix, "to_dict", lambda: {})(),
        }
