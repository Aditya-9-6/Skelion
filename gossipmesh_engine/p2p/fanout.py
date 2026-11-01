class FanoutController:
    def __init__(self, node_id: str):
        self.node_id = node_id

        class MockMatrix:
            def record_ack(self, peer_id, success):
                pass

            def to_dict(self):
                return {}

        self.matrix = MockMatrix()

    def record_ack(self, peer_id: str, success: bool):
        self.matrix.record_ack(peer_id, success)

    def compute_fanout(self) -> int:
        return 3

    def get_metrics(self) -> dict:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix.to_dict(),
        }
