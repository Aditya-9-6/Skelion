from skelion_agent.throttler import AdaptiveConcurrencyThrottler


def test_throttler_happy_path():
    throttler = AdaptiveConcurrencyThrottler(max_tokens=10.0, refill_rate=5.0)
    # Acquire within bucket capacity
    assert throttler.acquire(cpu_load=50.0, memory_load=50.0, cost=2.0) is True
    metrics = throttler.get_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["passed_requests"] == 1
    assert metrics["dropped_requests"] == 0


def test_throttler_capacity_exhaustion():
    throttler = AdaptiveConcurrencyThrottler(max_tokens=5.0, refill_rate=1.0)
    # Exhaust tokens
    assert throttler.acquire(cpu_load=10.0, memory_load=10.0, cost=5.0) is True
    # Next request should be dropped due to empty token bucket
    assert throttler.acquire(cpu_load=10.0, memory_load=10.0, cost=1.0) is False
    metrics = throttler.get_metrics()
    assert metrics["passed_requests"] == 1
    assert metrics["dropped_requests"] == 1


def test_throttler_cpu_memory_shedding():
    throttler = AdaptiveConcurrencyThrottler(
        max_tokens=10.0, refill_rate=10.0, cpu_threshold=80.0, memory_threshold=80.0
    )
    # CPU over threshold should shed immediately regardless of tokens
    assert throttler.acquire(cpu_load=85.0, memory_load=50.0, cost=1.0) is False
    # Memory over threshold should shed immediately
    assert throttler.acquire(cpu_load=50.0, memory_load=90.0, cost=1.0) is False
    metrics = throttler.get_metrics()
    assert metrics["dropped_requests"] == 2


def test_throttler_config_update():
    throttler = AdaptiveConcurrencyThrottler(max_tokens=5.0, refill_rate=1.0)
    throttler.update_config(max_tokens=20.0, cpu_threshold=95.0)
    assert throttler.max_tokens == 20.0
    assert throttler.cpu_threshold == 95.0
