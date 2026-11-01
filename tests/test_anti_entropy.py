import asyncio
import pytest

from skelion_agent.anti_entropy import EphemeralAntiEntropyNode


@pytest.mark.asyncio
async def test_anti_entropy_convergence():
    # Initialize two ephemeral nodes on different ports
    node1 = EphemeralAntiEntropyNode(
        "127.0.0.1", 19001, state={"keyA": "val1"}, sync_interval=0.1
    )
    node2 = EphemeralAntiEntropyNode(
        "127.0.0.1", 19002, state={"keyB": "val2"}, sync_interval=0.1
    )

    node1.add_peer("127.0.0.1", 19002)
    node2.add_peer("127.0.0.1", 19001)

    await node1.start()
    await node2.start()

    try:
        # Mutate state on node1
        node1.update_state("keyB", "val2_updated")

        # Wait for anti-entropy sync cycle and convergence
        await asyncio.sleep(0.4)

        # Verify state convergence across both nodes
        assert node2.state.get("keyB") == "val2_updated"
        assert node1.merkle_tree.get_root_hash() == node2.merkle_tree.get_root_hash()
    finally:
        await node1.stop()
        await node2.stop()
