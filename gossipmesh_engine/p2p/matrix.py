class ReachabilityMatrix:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.reachability = {}

    def average_reachability(self) -> float:
        if not self.reachability:
            return 1.0
        return sum(self.reachability.values()) / len(self.reachability)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "reachability": self.reachability,
            "average": self.average_reachability(),
        }
