class FanoutMatrix:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.reachability = {}

    def record_ack(self, peer_id: str, success: bool):
        self.reachability[peer_id] = success

    def compute_fanout(self) -> int:
        return len(self.reachability)

    def get_metrics(self) -> dict:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.to_dict(),
        }
