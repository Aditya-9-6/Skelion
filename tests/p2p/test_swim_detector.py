import asyncio
import pytest
from skelion_agent.p2p.swim import SWIMProtocol
from skelion_agent.p2p.state import NodeState

@pytest.mark.asyncio
async def test_swim_node_lifecycle():
    node1 = SWIMProtocol(node_id="node-1", host="127.0.0.1", port=9001, probe_interval=0.1, suspicion_timeout=0.5)
    node2 = SWIMProtocol(node_id="node-2", host="127.0.0.1", port=9002, probe_interval=0.1, suspicion_timeout=0.5)

    await node1.start()
    await node2.start()

    node1.cluster.upsert("node-2", "127.0.0.1", 9002, NodeState.ALIVE, 0)
    node2.cluster.upsert("node-1", "127.0.0.1", 9001, NodeState.ALIVE, 0)

    await asyncio.sleep(0.3)

    m2 = node1.cluster.get("node-2")
    assert m2 is not None
    assert m2.state == NodeState.ALIVE

    await node1.stop()
    await node2.stop()

@pytest.mark.asyncio
async def test_swim_suspicion_timeout():
    node1 = SWIMProtocol(node_id="node-1", host="127.0.0.1", port=9003, probe_interval=0.1, suspicion_timeout=0.2)
    await node1.start()

    target = node1.cluster.upsert("node-dead", "127.0.0.1", 9999, NodeState.ALIVE, 0)
    node1._suspect_node(target)
    assert target.state == NodeState.SUSPECT

    await asyncio.sleep(0.3)
    node1._check_suspicion_timeouts()
    assert target.state == NodeState.DEAD

    await node1.stop()
