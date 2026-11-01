import threading
from skelion_agent.core.cache_oblivious_btree import CacheObliviousBTree


def test_btree_basic_operations():
    btree = CacheObliviousBTree(node_capacity=4)
    assert len(btree) == 0

    # Insert items
    data = [(10, "val_10"), (20, "val_20"), (5, "val_5"), (15, "val_15"), (1, "val_1")]
    for k, v in data:
        btree.insert(k, v)

    assert len(btree) == 5

    # Search items
    assert btree.search(10) == "val_10"
    assert btree.search(1) == "val_1"
    assert btree.search(99) is None


def test_btree_range_query():
    btree = CacheObliviousBTree(node_capacity=4)
    for i in range(100):
        btree.insert(i, f"val_{i}")

    results = btree.range_query(20, 25)
    expected = [
        (20, "val_20"),
        (21, "val_21"),
        (22, "val_22"),
        (23, "val_23"),
        (24, "val_24"),
        (25, "val_25"),
    ]
    assert results == expected

    empty_results = btree.range_query(200, 300)
    assert empty_results == []


def test_btree_concurrent_access():
    btree = CacheObliviousBTree(node_capacity=8)
    for i in range(500):
        btree.insert(i, f"val_{i}")

    errors = []

    def reader_worker():
        try:
            for _ in range(100):
                res = btree.search(250)
                assert res == "val_250"
                rng = btree.range_query(10, 20)
                assert len(rng) == 11
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reader_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(btree) == 500


def test_btree_clear():
    btree = CacheObliviousBTree(node_capacity=4)
    btree.insert(1, "a")
    btree.insert(2, "b")
    assert len(btree) == 2
    btree.clear()
    assert len(btree) == 0
    assert btree.search(1) is None
