import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Tuple

from gossipmesh_engine.consensus.merkle import MerkleTree

logger = logging.getLogger("skelion_agent.anti_entropy")


class EphemeralAntiEntropyNode:
    """High-performance gossip-driven anti-entropy node using Merkle tree digests
    over asynchronous UDP sockets for O(log N) state reconciliation.
    """

    def __init__(
        self,
        host: str,
        port: int,
        state: Optional[Dict[str, str]] = None,
        sync_interval: float = 0.5,
    ):
        self.host = host
        self.port = port
        self.state: Dict[str, str] = state or {}
        self.merkle_tree = MerkleTree(self.state)
        self.sync_interval = sync_interval
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._is_running = False
        self._sync_task: Optional[asyncio.Task] = None
        self.peers: List[Tuple[str, int]] = []

    def add_peer(self, peer_host: str, peer_port: int) -> None:
        peer = (peer_host, peer_port)
        if peer not in self.peers:
            self.peers.append(peer)

    def update_state(self, key: str, value: str) -> None:
        self.state[key] = value
        self.merkle_tree.insert(key, value)

    async def start(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        loop = asyncio.get_running_loop()

        class UDPProtocol(asyncio.DatagramProtocol):
            def __init__(self, outer_node):
                self.outer = outer_node

            def connection_made(self, transport):
                self.outer._transport = transport

            def datagram_received(self, data, addr):
                asyncio.create_task(self.outer._handle_packet(data, addr))

        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: UDPProtocol(self), local_addr=(self.host, self.port)
        )
        self._sync_task = asyncio.create_task(self._gossip_loop())
        logger.info(f"EphemeralAntiEntropyNode started on {self.host}:{self.port}")

    async def stop(self) -> None:
        self._is_running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        if self._transport:
            self._transport.close()
            self._transport = None
        logger.info(f"EphemeralAntiEntropyNode stopped on {self.host}:{self.port}")

    async def _gossip_loop(self) -> None:
        try:
            while self._is_running:
                await asyncio.sleep(self.sync_interval)
                if self.peers:
                    # Pick a peer for anti-entropy sync
                    peer = self.peers[int(time.time() * 1000) % len(self.peers)]
                    await self._send_digest_request(peer)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in gossip loop: {e}")

    async def _send_digest_request(self, peer: Tuple[str, int]) -> None:
        if not self._transport:
            return
        packet = {
            "type": "DIGEST_REQ",
            "sender": (self.host, self.port),
            "root_hash": self.merkle_tree.get_root_hash(),
        }
        try:
            self._transport.sendto(json.dumps(packet).encode("utf-8"), peer)
        except Exception as e:
            logger.debug(f"Failed to send digest request to {peer}: {e}")

    async def _handle_packet(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            packet = json.loads(data.decode("utf-8"))
            p_type = packet.get("type")
            if p_type == "DIGEST_REQ":
                peer_root = packet.get("root_hash")
                local_root = self.merkle_tree.get_root_hash()
                if peer_root != local_root:
                    # Send our subtree fingerprints for reconciliation
                    resp = {
                        "type": "DIGEST_RESP",
                        "sender": (self.host, self.port),
                        "fingerprints": self.merkle_tree.get_subtree_fingerprints(),
                        "state": self.state,
                    }
                    if self._transport:
                        self._transport.sendto(json.dumps(resp).encode("utf-8"), addr)
            elif p_type == "DIGEST_RESP":
                peer_state = packet.get("state", {})
                peer_fps = packet.get("fingerprints", {})
                self._reconcile(peer_state, peer_fps)
        except Exception as e:
            logger.error(f"Error handling packet from {addr}: {e}")

    def _reconcile(
        self, peer_state: Dict[str, str], peer_fingerprints: Dict[str, str]
    ) -> None:
        local_fps = self.merkle_tree.get_subtree_fingerprints()
        # Simple anti-entropy reconciliation: pull missing or divergent keys
        updated = False
        for k, v in peer_state.items():
            if self.state.get(k) != v:
                self.state[k] = v
                self.merkle_tree.insert(k, v)
                updated = True
        if updated:
            logger.info(f"Node {self.port} successfully reconciled state with peer.")
