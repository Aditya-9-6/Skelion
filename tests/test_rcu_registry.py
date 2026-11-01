import pytest
import threading
import time
from skelion_agent.core.rcu_registry import RCURegistry, RCUEpochTracker


def test_rcu_basic_lookup_and_update():
    registry = RCURegistry({"agent_1": "endpoint_a"})
    
    assert registry.lookup("agent_1") == "endpoint_a"
    assert registry.lookup("nonexistent") is None

    registry.update_route("agent_1", "endpoint_b")
    assert registry.lookup("agent_1") == "endpoint_b"

    registry.update_route(
        "agent_2", "endpoint_c"
    )
    assert registry.lookup("agent_2") == "endpoint_c"

    assert registry.remove_route("agent_1") is True
    assert registry.lookup("agent_1") is None
    assert registry.remove_route("agent_1") is False


def test_rcu_concurrent_reads_and_writes():
    registry = RCURegistry({"base_route": "v1"})
    stop_event = threading.Event()
    errors = []

    def reader_worker():
        while not stop_event.is_set():
            val = registry.lookup("base_route")
            if val not in ("v1", "v2", "v3"):
                errors.append(f"Unexpected value found: {val}")
            time.sleep(0.0001)

    def writer_worker():
        for i in range(50):
            val = "v2" if i % 2 == 0 else "v3"
            registry.update_route("base_route", val)
            time.sleep(0.001)

    threads = [threading.Thread(target=reader_worker) for _ in range(8)]
    writer = threading.Thread(target=writer_worker)

    for t in threads:
        t.start()
    writer.start()

    writer.join()
    stop_event.set()

    for t in threads:
        t.join()

    assert not errors, f"Concurrent RCU reader/writer race or corruption detected: {errors}"


def test_epoch_tracker_reclamation():
    tracker = RCUEpochTracker()
    ep1 = tracker.enter_critical_section()
    assert ep1 == 0
    
    new_ep = tracker.advance_epoch()
    assert new_ep == 1
    
    # Cannot reclaim yet because current thread is in ep0
    assert tracker.can_reclaim(1) is False
    
    tracker.exit_critical_section()
    # Now no threads are in critical section, can reclaim up to new_ep
    assert tracker.can_reclaim(1) is True
