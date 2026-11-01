import pytest
import threading
from skelion_agent.probabilistic_filter import ProbabilisticFilterMesh


def test_probabilistic_filter_basic():
    pf = ProbabilisticFilterMesh(capacity=1000, error_rate=0.01)
    assert "anomaly_123" not in pf
    
    pf.add("anomaly_123")
    assert "anomaly_123" in pf
    assert pf.might_contain("anomaly_123") is True


def test_probabilistic_filter_false_positives():
    pf = ProbabilisticFilterMesh(capacity=5000, error_rate=0.05)
    
    # Insert 5000 items
    inserted = [f"telemetry_stream_{i}" for i in range(5000)]
    for item in inserted:
        pf.add(item)

    # Verify all inserted items are present
    for item in inserted:
        assert item in pf

    # Check false positive rate for uninserted items
    false_positives = 0
    test_count = 1000
    for i in range(test_count):
        item = f"unseen_stream_{i}"
        if item in pf:
            false_positives += 1

    fp_rate = false_positives / test_count
    # Allow a reasonable margin above configured error rate due to stochastic variance
    assert fp_rate < 0.20


def test_probabilistic_filter_concurrency():
    pf = ProbabilisticFilterMesh(capacity=10000, error_rate=0.01)
    threads = []
    num_threads = 8
    items_per_thread = 500

    def worker(thread_idx: int):
        for i in range(items_per_thread):
            item = f"concurrent_item_{thread_idx}_{i}"
            pf.add(item)

    for t in range(num_threads):
        th = threading.Thread(target=worker, args=(t,))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    # Verify all items inserted concurrently are present
    for t in range(num_threads):
        for i in range(items_per_thread):
            assert f"concurrent_item_{t}_{i}" in pf


def test_probabilistic_filter_clear_and_fill_ratio():
    pf = ProbabilisticFilterMesh(capacity=100, error_rate=0.05)
    assert pf.fill_ratio == 0.0
    
    for i in range(50):
        pf.add(f"item_{i}")
    
    assert pf.fill_ratio > 0.0
    
    pf.clear()
    assert pf.fill_ratio == 0.0
    assert "item_0" not in pf


def test_probabilistic_filter_invalid_params():
    with pytest.raises(ValueError):
        ProbabilisticFilterMesh(capacity=0)
    with pytest.raises(ValueError):
        ProbabilisticFilterMesh(capacity=100, error_rate=1.5)
