import threading
import pytest
from skelion_agent.core.concurrent_map import ConcurrentHashMap


def test_concurrent_map_basic_operations():
    cmap = ConcurrentHashMap(capacity=16)
    assert cmap.get("missing") is None

    cmap.put("key1", "val1")
    cmap.put("key2", "val2")

    assert cmap.get("key1") == "val1"
    assert cmap.get("key2") == "val2"

    assert cmap.remove("key1") is True
    assert cmap.get("key1") is None
    assert cmap.remove("key1") is False


def test_concurrent_map_resize():
    cmap = ConcurrentHashMap(capacity=4, load_factor_threshold=0.5)
    for i in range(20):
        cmap.put(f"key_{i}", f"val_{i}")

    assert cmap.size == 20
    for i in range(20):
        assert cmap.get(f"key_{i}") == f"val_{i}"


def test_concurrent_map_multithreaded_contention():
    cmap = ConcurrentHashMap(capacity=128)
    threads = []

    def worker(start_idx, count):
        for i in range(start_idx, start_idx + count):
            cmap.put(f"k_{i}", i)
            assert cmap.get(f"k_{i}") == i

    for t_id in range(4):
        t = threading.Thread(target=worker, args=(t_id * 50, 50))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert cmap.size == 200
    for i in range(200):
        assert cmap.get(f"k_{i}") == i


def test_concurrent_map_clear():
    cmap = ConcurrentHashMap(capacity=16)
    cmap.put("a", 1)
    cmap.put("b", 2)
    assert cmap.size == 2
    cmap.clear()
    assert cmap.size == 0
    assert cmap.get("a") is None
