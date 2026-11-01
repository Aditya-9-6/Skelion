import threading
import time
import random
import pytest
from skelion_agent.core.rcu_registry import RCURegistry, RCUEpochTracker


def test_rcu_basic_operations():
    registry = RCURegistry({"route_a": "handler_1"})
    assert registry.get("route_a") == "handler_1"
    assert registry.get("nonexistent", "default") == "default"

    registry.set_route("route_b", "handler_2")
    assert registry.get("route_b") == "handler_2"
    assert registry.get_all() == {"route_a": "handler_1", "route_b": "handler_2"}

    registry.remove_route("route_a")
    assert registry.get("route_a") is None
    assert registry.get_all() == {"route_b": "handler_2"}


def test_rcu_concurrent_read_write():
    registry = RCURegistry({"base": "initial"})
    stop_event = threading.Event()
    errors = []

    def reader_worker():
        while not stop_event.is_set():
            try:
                val = registry.get("base")
                all_map = registry.get_all()
                if val is None or not isinstance(all_map, dict):
                    errors.append(f"Invalid read value: {val}, map: {all_map}")
            except Exception as e:
                errors.append(e)

    def writer_worker():
        i = 0
        while not stop_event.is_set() and i < 100:
            try:
                registry.set_route(f"key_{i}", f"val_{i}")
                if i > 10:
                    registry.remove_route(f"key_{i-10}")
                i += 1
                time.sleep(0.001)
            except Exception as e:
                errors.append(e)

    readers = [threading.Thread(target=reader_worker) for _ in range(8)]
    writers = [threading.Thread(target=writer_worker) for _ in range(2)]

    for r in readers:
        r.start()
    for w in writers:
        w.start()

    time.sleep(0.2)
    stop_event.set()

    for r in readers:
        r.join()
    for w in writers:
        w.join()

    assert not errors, f"Concurrent errors encountered: {errors}"


def test_epoch_tracker():
    tracker = RCUEpochTracker()
    e1 = tracker.enter()
    assert tracker.can_reclaim(e1) is False
    
    e2 = tracker.advance()
    assert tracker.can_reclaim(e1) is False
    
    tracker.exit(e1)
    assert tracker.can_reclaim(e1) is True
