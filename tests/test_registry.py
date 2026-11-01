import concurrent.futures
import random
import time

from skelion_agent.registry import HazardPointerRegistry


def test_registry_basic_crud():
    registry = HazardPointerRegistry()

    # Register
    node1 = registry.register_or_update("agent-001", {"status": "idle", "term": 1})
    assert node1.agent_id == "agent-001"
    assert node1.version == 1
    assert node1.state["status"] == "idle"

    # Read via hazard pointer
    hp = registry.acquire_hazard_pointer("agent-001")
    assert hp is not None
    assert hp.state["status"] == "idle"
    registry.release_hazard_pointer()

    # Update
    node2 = registry.register_or_update(
        "agent-001", {"status": "remediating", "term": 1}
    )
    assert node2.version == 2
    assert node2.state["status"] == "remediating"

    # Unregister
    assert registry.unregister("agent-001") is True
    assert registry.acquire_hazard_pointer("agent-001") is None
    assert registry.unregister("agent-001") is False


def test_concurrent_hazard_pointer_readers_and_writers():
    registry = HazardPointerRegistry(gc_batch_threshold=10)
    agent_ids = [f"agent-{i}" for i in range(5)]

    # Initialize agents
    for aid in agent_ids:
        registry.register_or_update(aid, {"count": 0})

    stop_event = False

    def reader_worker():
        nonlocal stop_event
        reads = 0
        while not stop_event:
            aid = random.choice(agent_ids)
            hp = registry.acquire_hazard_pointer(aid)
            if hp is not None:
                # Access protected state safely
                assert "count" in hp.state
            registry.release_hazard_pointer()
            reads += 1
        return reads

    def writer_worker():
        nonlocal stop_event
        writes = 0
        while not stop_event:
            aid = random.choice(agent_ids)
            current = registry.acquire_hazard_pointer(aid)
            val = (current.state["count"] + 1) if current else 1
            registry.release_hazard_pointer()
            registry.register_or_update(aid, {"count": val})
            writes += 1
        return writes

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(reader_worker) for _ in range(4)] + [
            executor.submit(writer_worker) for _ in range(2)
        ]

        time.sleep(0.5)
        stop_event = True
        results = [f.result() for f in futures]

    assert sum(results) > 0
    stats = registry.get_stats()
    assert stats["active_agents"] == len(agent_ids)

    # Force GC and check cleanup
    surviving = registry.force_gc()
    assert isinstance(surviving, int)
