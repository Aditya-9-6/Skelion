import threading
from skelion_agent.skip_list import ConcurrentSkipList


def test_skip_list_basic_operations():
    sl = ConcurrentSkipList()
    assert sl.search("key1") is None

    assert sl.insert("key1", "value1") is True
    assert sl.search("key1") == "value1"

    # Duplicate insert updates value and returns False
    assert sl.insert("key1", "value2") is False
    assert sl.search("key1") == "value2"

    # Deletion
    assert sl.delete("key1") == "value2"
    assert sl.search("key1") is None
    assert sl.delete("key1") is None


def test_skip_list_concurrent_stress():
    sl = ConcurrentSkipList()
    num_threads = 8
    items_per_thread = 50

    def worker(thread_idx):
        for i in range(items_per_thread):
            key = f"t{thread_idx}-k{i}"
            val = f"val-{thread_idx}-{i}"
            sl.insert(key, val)
            assert sl.search(key) == val

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    # Verify all inserted items are readable
    for t in range(num_threads):
        for i in range(items_per_thread):
            key = f"t{t}-k{i}"
            assert sl.search(key) == f"val-{t}-{i}"
