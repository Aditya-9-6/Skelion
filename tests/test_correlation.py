import threading
from skelion_agent.correlation import IncidentCorrelationEngine, CountMinSketch


def test_count_min_sketch():
    sketch = CountMinSketch(width=512, depth=3)
    sketch.add("service_a", 5)
    sketch.add("service_b", 2)

    assert sketch.estimate("service_a") >= 5
    assert sketch.estimate("service_b") >= 2
    assert sketch.estimate("non_existent") <= 2


def test_trie_insertion_and_correlation():
    engine = IncidentCorrelationEngine(max_nodes=100)

    engine.insert_path(
        ["auth-service", "db-timeout", "pool-exhaustion"], {"error_code": 503}
    )
    engine.insert_path(
        ["auth-service", "db-timeout", "pool-exhaustion"], {"error_code": 503}
    )
    engine.insert_path(["auth-service", "redis-latency"], {"error_code": 504})

    results = engine.correlate(["auth-service"])
    assert len(results) > 0
    assert results[0]["incident_count"] >= 2


def test_concurrency_safety():
    engine = IncidentCorrelationEngine(max_nodes=1000)

    def worker(prefix_list):
        for p in prefix_list:
            engine.insert_path(p, {"thread": threading.get_ident()})

    paths = [
        ["api-gateway", "service-x", "error-500"],
        ["api-gateway", "service-y", "error-502"],
        ["auth", "token-expired"],
    ]

    threads = [threading.Thread(target=worker, args=(paths * 10,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    results = engine.correlate(["api-gateway"])
    assert len(results) > 0
