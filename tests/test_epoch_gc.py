import threading
import time
import pytest
from skelion_agent.core.epoch_gc import (
    EpochManager,
    HazardPointerRegistry,
    EpochGarbageCollector,
    GLOBAL_EPOCH_GC,
)


def test_epoch_manager_basic():
    em = EpochManager()
    assert em.current_epoch == 0
    assert em.min_active_epoch() == 0

    ep = em.enter()
    assert ep == 0
    assert em.min_active_epoch() == 0

    em.advance()
    assert em.current_epoch == 1

    em.exit()
    assert em.min_active_epoch() == 1


voices = []

class DummyNode:
    def __init__(self, name: str):
        self.name = name


def test_hazard_pointer_registry():
    registry = HazardPointerRegistry()
    node = DummyNode("test_node")

    assert len(registry.get_protected_ids()) == 0
    registry.protect(node)
    assert id(node) in registry.get_protected_ids()

    registry.clear()
    assert len(registry.get_protected_ids()) == 0


def test_epoch_garbage_collector_lifecycle():
    gc = EpochGarbageCollector(cleanup_interval_retirements=2)
    reclaimed = []

    def make_destructor(name):
        def _destruct():
            reclaimed.append(name)
        return _destruct

    # Retire nodes
    gc.retire(make_destructor("node_1"))
    gc.retire(make_destructor("node_2"))

    # Force collection cycle
    count = gc.collect()
    assert count >= 1
    assert "node_1" in reclaimed or "node_2" in reclaimed


def test_concurrent_epoch_stress():
    gc = EpochGarbageCollector(cleanup_interval_retirements=10)
    reclaimed_count = 0
    lock = threading.Lock()

    def worker_task(worker_id: int):
        nonlocal reclaimed_count
        for i in range(50):
            gc.epoch_manager.enter()
            node = DummyNode(f"worker_{worker_id}_node_{i}")
            gc.hazard_registry.protect(node)
            time.sleep(0.001)
            gc.hazard_registry.clear()
            gc.epoch_manager.exit()

            gc.retire(lambda: nonlocal_increment())

    def nonlocal_increment():
        nonlocal reclaimed_count
        with lock:
            reclaimed_count += 1

    threads = [threading.Thread(target=worker_task, args=(w,)) for w in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    gc.collect()
    assert reclaimed_count > 0
