import pytest
import threading
from skelion_agent.core.skip_list import ConcurrentSkipList
from skelion_agent.core.memory_reclamation import EpochManager


def test_skip_list_basic_operations():
    sl = ConcurrentSkipList()
    assert sl.insert("agent_1", {"status": "active"}) is True
    assert sl.search("agent_1") == {"status": "active"}
    assert sl.insert("agent_1", {"status": "idle"}) is False
    assert sl.search("agent_1") == {"status": "idle"}
    assert sl.delete("agent_1") is True
    assert sl.search("agent_1") is None
    assert sl.delete("agent_1") is False


def test_skip_list_range_scan():
    sl = ConcurrentSkipList()
    for i in range(10):
        sl.insert(f"key_{i:02d}", i)

    results = list(sl.range_scan("key_03", "key_07"))
    expected = [(f"key_{i:02d}", i) for i in range(3, 8)]
    assert results == expected


def test_concurrent_skip_list_stress():
    sl = ConcurrentSkipList(EpochManager(num_threads=16))
    errors = []

    def worker(start_val: int):
        try:
            for i in range(100):
                k = f"key_{start_val}_{i}"
                sl.insert(k, i)
                sl.search(k)
                if i % 2 == 0:
                    sl.delete(k)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert len(errors) == 0
