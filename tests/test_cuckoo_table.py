import concurrent.futures

from skelion_agent.cuckoo_table import EpollCuckooHashTable


def test_cuckoo_table_basic_operations():
    table = EpollCuckooHashTable(capacity=16)
    try:
        assert table.get("route_alpha") is None

        assert table.put("route_alpha", "gateway_us_east") is True
        assert table.get("route_alpha") == "gateway_us_east"

        # Update existing
        assert table.put("route_alpha", "gateway_eu_west") is True
        assert table.get("route_alpha") == "gateway_eu_west"

        # Delete
        assert table.delete("route_alpha") is True
        assert table.get("route_alpha") is None
        assert table.delete("route_alpha") is False
    finally:
        table.close()


def test_cuckoo_table_evictions_and_stash():
    # Small capacity to trigger evictions and stash overflow
    table = EpollCuckooHashTable(capacity=4, max_evictions=10, stash_limit=8)
    try:
        routes = [
            ("route_1", "val_1"),
            ("route_2", "val_2"),
            ("route_3", "val_3"),
            ("route_4", "val_4"),
            ("route_5", "val_5"),
            ("route_6", "val_6"),
        ]

        for k, v in routes:
            assert table.put(k, v) is True

        for k, v in routes:
            assert table.get(k) == v
    finally:
        table.close()


def test_cuckoo_table_epoll_notifications():
    table = EpollCuckooHashTable(capacity=16)
    try:
        assert table.poll_events(timeout=0.01) is False

        table.put("telemetry_metric_1", "cpu_utilization")
        assert table.poll_events(timeout=0.1) is True

        # Subsequent poll without mutations should be False
        assert table.poll_events(timeout=0.01) is False
    finally:
        table.close()


def test_cuckoo_table_concurrent_contention():
    table = EpollCuckooHashTable(capacity=256)
    num_threads = 8
    items_per_thread = 50

    def worker(thread_id: int):
        for i in range(items_per_thread):
            key = f"key_{thread_id}_{i}"
            val = f"val_{thread_id}_{i}"
            assert table.put(key, val) is True
            retrieved = table.get(key)
            assert retrieved == val

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, t) for t in range(num_threads)]
            concurrent.futures.wait(futures)
            for f in futures:
                f.result()

        # Verify retrieval after concurrent writes
        for thread_id in range(num_threads):
            for i in range(items_per_thread):
                key = f"key_{thread_id}_{i}"
                assert table.get(key) == f"val_{thread_id}_{i}"
    finally:
        table.close()
