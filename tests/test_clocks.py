import threading
from gossipmesh_engine.core.clocks import VectorClock


def test_vector_clock_init_and_increment():
    vc = VectorClock("node1")
    assert vc.get_time("node1") == 0
    assert vc.increment() == 1
    assert vc.increment() == 2
    assert vc.get_time("node1") == 2


def test_vector_clock_update():
    vc1 = VectorClock("node1")
    vc1.increment()

    vc2 = VectorClock("node2", {"node1": 0, "node2": 0})
    vc2.update(vc1.snapshot())

    assert vc2.get_time("node1") == 1
    assert vc2.get_time("node2") == 0


def test_vector_clock_delta():
    vc = VectorClock("node1", {"node1": 5, "node2": 3, "node3": 1})
    known = {"node1": 3, "node2": 3, "node4": 0}

    d = vc.delta(known)
    assert d == {"node1": 5, "node3": 1}


def test_vector_clock_delta_iter():
    vc = VectorClock("node1", {"node1": 5, "node2": 3})
    known = {"node1": 4, "node2": 3}

    res = list(vc.delta_iter(known))
    assert res == [("node1", 5)]


def test_vector_clock_comparisons():
    vc = VectorClock("node1", {"node1": 2, "node2": 1})

    # EQUAL
    assert vc.compare({"node1": 2, "node2": 1}) == "EQUAL"

    # GREATER_THAN
    assert vc.compare({"node1": 1, "node2": 1}) == "GREATER_THAN"
    assert vc.compare({"node1": 2, "node2": 0}) == "GREATER_THAN"

    # LESS_THAN
    assert vc.compare({"node1": 3, "node2": 2}) == "LESS_THAN"

    # CONCURRENT
    assert vc.compare({"node1": 1, "node2": 2}) == "CONCURRENT"
    assert vc.compare({"node1": 2, "node3": 1}) == "CONCURRENT"


def test_vector_clock_thread_safety():
    vc = VectorClock("node1")
    threads = []

    def worker():
        for _ in range(100):
            vc.increment()
            vc.update({"node2": 1})

    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert vc.get_time("node1") == 1000
    assert vc.get_time("node2") == 1
