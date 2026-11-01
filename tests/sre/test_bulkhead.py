import time
import pytest
from skelion_agent.sre.bulkhead import AdaptiveBulkhead, BulkheadOverloadError


def test_bulkhead_happy_path():
    bulkhead = AdaptiveBulkhead(name="test-agent-pool", initial_concurrency=5)
    assert bulkhead.current_limit == 5
    assert bulkhead.active_requests == 0

    with bulkhead as bh:
        assert bh.active_requests == 1

    assert bulkhead.active_requests == 0


def test_bulkhead_overload_rejection():
    bulkhead = AdaptiveBulkhead(name="tight-pool", initial_concurrency=1, min_concurrency=1, max_concurrency=1)
    
    # Manually saturate
    assert bulkhead.acquire() is True
    assert bulkhead.active_requests == 1

    with pytest.raises(BulkheadOverloadError):
        with bulkhead:
            pass

    bulkhead.release()
    assert bulkhead.active_requests == 0


def test_dynamic_token_slicing_latency_adaptation():
    bulkhead = AdaptiveBulkhead(
        name="adaptive-pool",
        initial_concurrency=10,
        min_concurrency=2,
        max_concurrency=50,
        target_latency_ms=100.0,
    )

    initial_limit = bulkhead.current_limit

    # Simulate high latency exceeding target
    for _ in range(60):
        bulkhead.record_latency(300.0)

    # Concurrency limit should scale down due to high latency
    assert bulkhead.current_limit < initial_limit

    reduced_limit = bulkhead.current_limit

    # Simulate low latency well under target
    for _ in range(60):
        bulkhead.record_latency(20.0)

    # Concurrency limit should scale back up
    assert bulkhead.current_limit > reduced_limit
