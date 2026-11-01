import time
from enum import Enum
from typing import Dict, Optional, Any, Set


class NodeState(str, Enum):
    ALIVE = "alive"
    SUSPECT = "suspect"
    DEAD = "dead"
    LEFT = "left"


class MemberNode:
    __slots__ = (
        "node_id",
        "host",
        "port",
        "state",
        "incarnation",
        "last_updated",
        "suspicion_start",
    )

    def __init__(
        self,
        node_id: str,
        host: str,
        port: int,
        state: NodeState = NodeState.ALIVE,
        incarnation: int = 0,
    ):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.state = state
        self.incarnation = incarnation
        self.last_updated = time.monotonic()
        self.suspicion_start: Optional[float] = None

    def update(self, state: NodeState, incarnation: int) -> bool:
        updated = False
        if incarnation > self.incarnation:
            self.incarnation = incarnation
            self.state = state
            self.last_updated = time.monotonic()
            if state == NodeState.ALIVE:
                self.suspicion_start = None
            elif state == NodeState.SUSPECT and not self.suspicion_start:
                self.suspicion_start = time.monotonic()
            updated = True
        elif incarnation == self.incarnation:
            if self.state == NodeState.ALIVE and state == NodeState.SUSPECT:
                self.state = NodeState.SUSPECT
                self.suspicion_start = time.monotonic()
                self.last_updated = time.monotonic()
                updated = True
            elif self.state == NodeState.SUSPECT and state == NodeState.ALIVE:
                self.state = NodeState.ALIVE
                self.suspicion_start = None
                self.last_updated = time.monotonic()
                updated = True
        return updated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "state": self.state.value,
            "incarnation": self.incarnation,
            "last_updated": self.last_updated,
            "suspicion_start": self.suspicion_start,
        }


class ClusterState:
    def __init__(self, local_node_id: str):
        self.local_node_id = local_node_id
        self.members: Dict[str, MemberNode] = {}

    def upsert(
        self,
        node_id: str,
        host: str,
        port: int,
        state: NodeState = NodeState.ALIVE,
        incarnation: int = 0,
    ) -> MemberNode:
        if node_id not in self.members:
            self.members[node_id] = MemberNode(node_id, host, port, state, incarnation)
        else:
            self.members[node_id].update(state, incarnation)
        return self.members[node_id]

    def get(self, node_id: str) -> Optional[MemberNode]:
        return self.members.get(node_id)

    def remove(self, node_id: str) -> None:
        self.members.pop(node_id, None)

    def get_alive_members(self) -> Set[str]:
        return {nid for nid, m in self.members.items() if m.state == NodeState.ALIVE}

    def get_random_members(
        self, k: int, exclude: Optional[Set[str]] = None
    ) -> List[MemberNode]:
        import random

        exclude = exclude or set()
        candidates = [
            m
            for nid, m in self.members.items()
            if nid not in exclude and m.state != NodeState.DEAD
        ]
        if not candidates:
            return []
        return random.sample(candidates, min(k, len(candidates)))
