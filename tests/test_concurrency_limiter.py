# tests/test_concurrency_limiter.py - Comprehensive Unit Tests for Adaptive Concurrency Limiter

import time
import threading
import pytest
from skelion_agent.concurrency_limiter import (
    AdaptiveConcurrencyLimiter,
    ConcurrencyLimitExceededError,
)


def test_limiter_initialization():
    limiter = AdaptiveConcurrencyLimiter(initial_limit=50, min_limit=10, max_limit=200)
    assert limiter.current_limit == 50
    assert limiter.in_flight == 0
    stats = limiter.get_stats()
    assert stats["current_limit"] == 50
    assert stats["in_flight"] == 0


def test_acquire_and_release():
    limiter = AdaptiveConcurrencyLimiter(initial_limit=5, min_limit=1, max_limit=10)
    
    # Acquire slots up to limit
    for _ in range(5):
        assert limiter.acquire(timeout=0.1) is True
    
    assert limiter.in_flight == 5
    
    # Next acquire should fail with zero timeout
    assert limiter.acquire(timeout=0.0) is False

    # Release one slot with low latency (should increase or maintain limit)
    limiter.release(latency_ms=50.0)
    assert limiter.in_flight == 4
    
    # Now acquire should succeed
    assert limiter.acquire(timeout=0.1) is True
    assert limiter.in_flight == 5


def test_littles_law_adaptation():
    limiter = AdaptiveConcurrencyLimiter(initial_limit=50, min_limit=10, max_limit=100, target_latency_ms=100.0)
    initial_limit = limiter.current_limit

    # Simulate high latency (slower than target) -> should decrease limit
    for _ in range(10):
        limiter.acquire(timeout=0.1)
        limiter.release(latency_ms=300.0)

    assert limiter.current_limit < initial_limit

    # Simulate low latency (faster than target) -> should recover limit
    for _ in range(10):
        if limiter.acquire(timeout=0.1):
            limiter.release(latency_ms=20.0)

    assert limiter.current_limit > limiter.min_limit


def test_enforce_admission_exception():
    limiter = AdaptiveConcurrencyLimiter(initial_limit=1, min_limit=1, max_limit=2)
    assert limiter.acquire(timeout=0.1) is True
    
    with pytest.raises(ConcurrencyLimitExceededError) as exc_info:
        limiter.enforce_admission()
    assert exc_info.value.status_code == 429
    assert "current_limit" in exc_info.value.details
    
    limiter.release(latency_ms=80.0)
    # Should not raise now
    limiter.enforce_admission()


def test_concurrent_load_safety():
    limiter = AdaptiveConcurrencyLimiter(initial_limit=20, min_limit=5, max_limit=100)
    errors = []

    def worker():
        try:
            for _ in range(50):
                if limiter.acquire(timeout=0.05):
                    time.sleep(0.001)
                    limiter.release(latency_ms=90.0)
                else:
                    time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    stats = limiter.get_stats()
    assert stats["total_requests"] > 0
