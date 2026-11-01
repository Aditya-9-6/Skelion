import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple

from skelion_agent.p2p.state import ClusterState, MemberNode, NodeState

logger = logging.getLogger(__name__)


class SWIMProtocol:
    def __init__(
        self,
        node_id: str,
        host: str,
        port: int,
        k_indirect: int = 3,
        probe_interval: float = 1.0,
        suspicion_timeout: float = 5.0,
    ):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.k_indirect = k_indirect
        self.probe_interval = probe_interval
        self.suspicion_timeout = suspicion_timeout

        self.cluster = ClusterState(node_id)
        self.incarnation = 0
        self.transport: Optional[asyncio.DatagramTransport] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._pending_probes: Dict[str, asyncio.Future] = {}

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: SWIMProtocolProtocol(self), local_addr=(self.host, self.port)
        )
        self._running = True
        self._task = asyncio.create_task(self._probe_loop())
        logger.info(
            f"SWIM protocol started for node {self.node_id} on {self.host}:{self.port}"
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.transport:
            self.transport.close()
        logger.info(f"SWIM protocol stopped for node {self.node_id}")

    def handle_datagram(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            msg = json.loads(data.decode("utf-8"))
            msg_type = msg.get("type")
            sender_id = msg.get("sender_id")

            if msg_type == "PING":
                self._handle_ping(msg, addr)
            elif msg_type == "ACK":
                self._handle_ack(msg, addr)
            elif msg_type == "INDIRECT_PROBE":
                self._handle_indirect_probe(msg, addr)
            elif msg_type == "INDIRECT_ACK":
                self._handle_indirect_ack(msg, addr)
            elif msg_type == "GOSSIP":
                self._handle_gossip(msg, addr)
        except Exception as e:
            logger.error(f"Error handling datagram from {addr}: {e}")

    def _send(self, payload: Dict[str, Any], addr: Tuple[str, int]) -> None:
        if self.transport:
            data = json.dumps(payload).encode("utf-8")
            self.transport.sendto(data, addr)

    async def _probe_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.probe_interval)
            await self._run_probe_round()
            self._check_suspicion_timeouts()

    async def _run_probe_round(self) -> None:
        members = self.cluster.get_random_members(1, exclude={self.node_id})
        if not members:
            return
        target = members[0]
        target_addr = (target.host, target.port)

        # Direct probe
        fut = asyncio.get_running_loop().create_future()
        self._pending_probes[target.node_id] = fut
        self._send(
            {
                "type": "PING",
                "sender_id": self.node_id,
                "incarnation": self.incarnation,
            },
            target_addr,
        )

        try:
            await asyncio.wait_for(fut, timeout=self.probe_interval * 0.8)
            # Success, node is alive
            target.update(NodeState.ALIVE, target.incarnation)
            return
        except asyncio.TimeoutError:
            pass
        finally:
            self._pending_probes.pop(target.node_id, None)

        # Fallback to indirect probing via k members
        indirect_candidates = self.cluster.get_random_members(
            self.k_indirect, exclude={self.node_id, target.node_id}
        )
        if not indirect_candidates:
            self._suspect_node(target)
            return

        indirect_futs = []
        for ind in indirect_candidates:
            ind_fut = asyncio.get_running_loop().create_future()
            self._pending_probes[f"{target.node_id}_via_{ind.node_id}"] = ind_fut
            indirect_futs.append(ind_fut)
            self._send(
                {
                    "type": "INDIRECT_PROBE",
                    "sender_id": self.node_id,
                    "target_id": target.node_id,
                    "target_host": target.host,
                    "target_port": target.port,
                },
                (ind.host, ind.port),
            )

        done, pending = await asyncio.wait(
            indirect_futs, timeout=self.probe_interval * 0.8
        )
        for f in pending:
            f.cancel()

        success = any(not f.cancelled() and f.exception() is None for f in done)
        if success:
            target.update(NodeState.ALIVE, target.incarnation)
        else:
            self._suspect_node(target)

    def _suspect_node(self, target: MemberNode) -> None:
        if target.state == NodeState.ALIVE:
            target.update(NodeState.SUSPECT, target.incarnation)
            logger.warning(
                f"Node {target.node_id} marked as SUSPECT due to probe timeout."
            )

    def _check_suspicion_timeouts(self) -> None:
        now = time.monotonic()
        for node_id, member in list(self.cluster.members.items()):
            if member.state == NodeState.SUSPECT and member.suspicion_start:
                if now - member.suspicion_start > self.suspicion_timeout:
                    member.state = NodeState.DEAD
                    logger.error(
                        f"Node {node_id} declared DEAD after suspicion timeout expired."
                    )

    def _handle_ping(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        sender_id = msg.get("sender_id")
        self._send(
            {"type": "ACK", "sender_id": self.node_id, "incarnation": self.incarnation},
            addr,
        )

    def _handle_ack(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        sender_id = msg.get("sender_id")
        fut = self._pending_probes.get(sender_id)
        if fut and not fut.done():
            fut.set_result(True)

    def _handle_indirect_probe(
        self, msg: Dict[str, Any], addr: Tuple[str, int]
    ) -> None:
        origin_id = msg.get("sender_id")
        target_id = msg.get("target_id")
        target_host = msg.get("target_host")
        target_port = msg.get("target_port")

        # Ping target directly
        async def probe_target():
            fut = asyncio.get_running_loop().create_future()
            self._pending_probes[f"indirect_{target_id}"] = fut
            self._send(
                {
                    "type": "PING",
                    "sender_id": self.node_id,
                    "incarnation": self.incarnation,
                },
                (target_host, target_port),
            )
            try:
                await asyncio.wait_for(fut, timeout=0.5)
                self._send(
                    {
                        "type": "INDIRECT_ACK",
                        "sender_id": self.node_id,
                        "target_id": target_id,
                        "success": True,
                    },
                    addr,
                )
            except Exception:
                self._send(
                    {
                        "type": "INDIRECT_ACK",
                        "sender_id": self.node_id,
                        "target_id": target_id,
                        "success": False,
                    },
                    addr,
                )
            finally:
                self._pending_probes.pop(f"indirect_{target_id}", None)

        asyncio.create_task(probe_target())

    def _handle_indirect_ack(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        target_id = msg.get("target_id")
        success = msg.get("success")
        # Find which indirect probe this fulfills
        for key, fut in list(self._pending_probes.items()):
            if key.startswith(f"{target_id}_via_") and not fut.done():
                if success:
                    fut.set_result(True)

    def _handle_gossip(self, msg: Dict[str, Any], addr: Tuple[str, int]) -> None:
        pass


class SWIMProtocolProtocol(asyncio.DatagramProtocol):
    def __init__(self, swim: SWIMProtocol):
        self.swim = swim

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        self.swim.handle_datagram(data, addr)
