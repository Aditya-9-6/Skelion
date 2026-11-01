import asyncio
import logging
from typing import Any, Dict, List, Optional
from gossipmesh.p2p.dht import KademliaDHT

logger = logging.getLogger(__name__)


class P2PNode:
    def __init__(self, node_id: Optional[str] = None, bind_address: str = "0.0.0.0:8000") -> None:
        self.bind_address = bind_address
        self.dht = KademliaDHT(node_id=node_id)
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info(f"P2P Node started with ID {self.dht.node_id} on {self.bind_address}")

    async def stop(self) -> None:
        self._running = False
        logger.info(f"P2P Node stopped")

    def register_peer(self, peer_id: str, address: str) -> bool:
        success = self.dht.add_peer(peer_id, address)
        if success:
            logger.info(f"Registered peer {peer_id} at {address}")
        else:
            logger.warning(f"Failed to register peer {peer_id}: Bucket full or error")
        return success

    def unregister_peer(self, peer_id: str) -> None:
        self.dht.remove_peer(peer_id)
        logger.info(f"Unregistered peer {peer_id}")

    def get_closest_peers(self, target_id: str, count: int = 5) -> List[Dict[str, str]]:
        nodes = self.dht.find_close_nodes(target_id, count)
        return [{"peer_id": pid, "address": addr} for pid, addr in nodes]
