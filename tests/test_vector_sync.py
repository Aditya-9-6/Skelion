from skelion_agent.consensus.vector_sync import (
    VectorClock,
    VectorClockSynchronizer,
    BoundedRingHistory,
)


def test_vector_clock_basic():
    vc1 = VectorClock("node-A")
    assert vc1.to_dict() == {"node-A": 0}

    vc1.increment()
    assert vc1.to_dict() == {"node-A": 1}


def test_vector_clock_comparison():
    vc1 = VectorClock("node-A", {"node-A": 1, "node-B": 0})
    vc2 = {"node-A": 2, "node-B": 0}

    assert vc1.compare(vc2) == "BEFORE"
    assert vc1.compare({"node-A": 0, "node-B": 1}) == "CONCURRENT"
    assert vc1.compare({"node-A": 1, "node-B": 0}) == "EQUAL"
    assert vc1.compare({"node-A": 0, "node-B": 0}) == "CONCURRENT_OR_AFTER"


def test_synchronizer_consensus_merge():
    sync_a = VectorClockSynchronizer("node-A")
    sync_b = VectorClockSynchronizer("node-B")

    entry_a = sync_a.set_state("remediation_status", "active")
    assert sync_a.get_state("remediation_status") == "active"

    # Sync A to B
    merged = sync_b.merge_state(entry_a)
    assert merged is True
    assert sync_b.get_state("remediation_status") == "active"

    # Try pushing stale entry from A to B
    stale_merged = sync_b.merge_state(entry_a)
    assert stale_merged is False


def test_concurrent_conflict_resolution():
    sync_a = VectorClockSynchronizer("node-A")
    sync_b = VectorClockSynchronizer("node-B")

    # Both set state concurrently without seeing each other's updates
    entry_a = sync_a.set_state("config", "v1-A")
    entry_b = sync_b.set_state("config", "v1-B")

    # Merge B into A
    merged_b_into_a = sync_a.merge_state(entry_b)
    assert merged_b_into_a is True
    snapshot = sync_a.get_consensus_snapshot()
    assert "config" in snapshot["state"]


def test_bounded_ring_history():
    ring = BoundedRingHistory(capacity=3)
    ring.append({"id": 1})
    ring.append({"id": 2})
    ring.append({"id": 3})
    ring.append({"id": 4})

    history = ring.get_all()
    assert len(history) == 3
    assert history[0]["id"] == 2
    assert history[2]["id"] == 4
