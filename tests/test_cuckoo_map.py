import threading
import time
from skelion_agent.cuckoo_map import EpollCuckooHashMap


def test_cuckoo_map_basic_operations():
    cmap = EpollCuckooHashMap(capacity=64)
    assert cmap.get("incident_1") is None

    assert cmap.put("incident_1", "routing_node_A") is True
    assert cmap.get("incident_1") == "routing_node_A"

    assert cmap.put("incident_1", "routing_node_B") is True
    assert cmap.get("incident_1") == "routing_node_B"

    assert cmap.delete("incident_1") is True
    assert cmap.get("incident_1") is None
    assert cmap.delete("incident_1") is False
    cmap.close()


def test_cuckoo_map_concurrent_ingestion():
    cmap = EpollCuckooHashMap(capacity=256)
    num_threads = 8
    items_per_thread = 50

    def worker(thread_id: int):
        for i in range(items_per_thread):
            key = f"incident_{thread_id}_{i}"
            val = f"node_{thread_id}"
            cmap.put(key, val)
            time.sleep(0.0001)
            res = cmap.get(key, thread_idx=thread_id)
            assert res == val

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for t_id in range(num_threads):
        for i in range(items_per_thread):
            key = f"incident_{t_id}_{i}"
            assert cmap.get(key, thread_idx=t_id) == f"node_{t_id}"

    cmap.close()


def test_cuckoo_map_epoll_notifications():
    cmap = EpollCuckooHashMap(capacity=32)
    has_epoll = cmap._has_epoll
    cmap.put("key_event", "val")
    if has_epoll:
        assert cmap.poll_events(timeout=0.1) is True
    cmap.close()
