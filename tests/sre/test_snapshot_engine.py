import pytest
from skelion_agent.sre.channel_tracker import BoundedFIFOChannelTracker
from skelion_agent.sre.snapshot_engine import ChandyLamportSnapshotEngine


@pytest.mark.asyncio
async def test_channel_tracker_basic():
    tracker = BoundedFIFOChannelTracker("chan-1", max_capacity=5)
    assert await tracker.send("msg1") is True
    assert await tracker.send("msg2") is True

    await tracker.start_recording()
    assert await tracker.send("msg3") is True
    recorded = await tracker.stop_recording()
    assert recorded == ["msg3"]

    assert await tracker.receive() == "msg1"
    assert await tracker.receive() == "msg2"
    assert await tracker.receive() == "msg3"
    assert await tracker.receive() is None


@pytest.mark.asyncio
async def test_snapshot_engine_initiation_and_markers():
    state = {"active_remediations": 2, "health": "ok"}
    engine = ChandyLamportSnapshotEngine("node-alpha", lambda: state)

    tracker_a = BoundedFIFOChannelTracker("chan-a")
    engine.register_channel("chan-a", tracker_a)

    snapshot = await engine.initiate_snapshot("snap-001")
    assert snapshot["snapshot_id"] == "snap-001"
    assert snapshot["node_id"] == "node-alpha"
    assert snapshot["local_state"] == state

    await tracker_a.send("in-flight-payload")
    updated = await engine.receive_marker("snap-001", "chan-a")
    assert "chan-a" in updated["in-flight_messages"]

    manifest_json = engine.get_serialized_manifest("snap-001")
    assert "snap-001" in manifest_json
    assert "checksum" in manifest_json
