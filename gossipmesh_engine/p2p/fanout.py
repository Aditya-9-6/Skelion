class FanoutMatrix:
    def __init__(self, node_id: str):
        self.node_id = node_id

    def record_ack(self, peer_id: str, success: bool):
        pass

    def to_dict(self):
        return {}


class FanoutMesh:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.matrix = FanoutMatrix(node_id)

    def compute_fanout(self) -> int:
        return 10

    def get_metrics(self) -> dict:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix.to_dict(),
        }
