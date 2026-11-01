import time
import threading
from skelion_agent.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerMesh,
    RingBuffer,
)


def test_ring_buffer_capacity():
    rb = RingBuffer(3)
    assert rb.get_values() == []
    rb.append(1.0)
    rb.append(0.0)
    assert rb.get_values() == [1.0, 0.0]
    rb.append(1.0)
    rb.append(0.0)
    assert rb.get_values() == [0.0, 1.0, 0.0]
    rb.clear()
    assert rb.get_values() == []


def test_circuit_breaker_closed_to_open():
    cb = CircuitBreaker(
        name="test",
        failure_rate_threshold=0.5,
        window_size=4,
        recovery_timeout=0.1,
        jitter=False,
    )
    assert cb.state == CircuitState.CLOSED

    # 2 failures out of 4 requests = 50% error rate
    assert cb.allow_request() is True
    cb.record_failure()
    assert cb.allow_request() is True
    cb.record_success()
    assert cb.allow_request() is True
    cb.record_failure()
    assert cb.allow_request() is True
    cb.record_success()

    # Current window: [1.0, 0.0, 1.0, 0.0] -> error rate 0.5 (meets threshold 0.5)
    # Record another failure to trip
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


def test_circuit_breaker_recovery_half_open():
    cb = CircuitBreaker(
        name="test_rec",
        failure_rate_threshold=0.5,
        window_size=2,
        recovery_timeout=0.05,
        half_open_max_probes=2,
        jitter=False,
    )
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False

    time.sleep(0.06)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Probe 1 success
    cb.record_success()
    # Probe 2 success
    assert cb.allow_request() is True
    cb.record_success()

    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_mesh():
    m = CircuitBreakerMesh()
    cb1 = m.get_or_create("service_a")
    cb2 = m.get_or_create("service_a")
    assert cb1 is cb2

    metrics = m.get_metrics()
    assert "service_a" in metrics
    assert metrics["service_a"]["state"] == "CLOSED"


def test_concurrency_safety():
    cb = CircuitBreaker(
        name="concurrent",
        failure_rate_threshold=0.8,
        window_size=100,
        recovery_timeout=1.0,
    )

    def worker():
        for _ in range(50):
            if cb.allow_request():
                if threading.get_ident() % 2 == 0:
                    cb.record_success()
                else:
                    cb.record_failure()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    metrics = cb.get_metrics()
    assert metrics["name"] == "concurrent"
