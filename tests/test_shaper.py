import time
import threading

from skelion_agent.sre.shaper import HierarchicalTokenBucketShaper, TokenBucket


def test_token_bucket_basic_consumption():
    bucket = TokenBucket(capacity=10.0, fill_rate=5.0)
    assert bucket.get_available_tokens() == 10.0

    # Consume valid amount
    assert bucket.consume(4.0) is True
    assert bucket.get_available_tokens() <= 6.0

    # Consume excessive amount
    assert bucket.consume(20.0) is False


def test_token_bucket_refill():
    bucket = TokenBucket(capacity=10.0, fill_rate=100.0)  # 100 tokens/sec
    assert bucket.consume(10.0) is True
    assert bucket.get_available_tokens() < 1.0

    # Sleep briefly to allow refill
    time.sleep(0.05)
    assert bucket.get_available_tokens() > 3.0


def test_hierarchical_bucket_shaping():
    shaper = HierarchicalTokenBucketShaper()
    # Global parent bucket limiting total throughput
    shaper.register_bucket("global", capacity=20.0, fill_rate=10.0)
    # Child tenant bucket
    shaper.register_bucket(
        "tenant_a", capacity=10.0, fill_rate=5.0, parent_name="global"
    )

    # Should succeed for both parent and child
    assert shaper.allow_request("tenant_a", cost=5.0) is True

    # Exceed child capacity
    assert shaper.allow_request("tenant_a", cost=15.0) is False


def test_concurrent_shaper_contention():
    shaper = HierarchicalTokenBucketShaper()
    shaper.register_bucket("high_throughput", capacity=1000.0, fill_rate=5000.0)

    results = []

    def worker():
        for _ in range(50):
            res = shaper.allow_request("high_throughput", cost=1.0)
            results.append(res)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify thread safety and execution completion
    assert len(results) == 500
