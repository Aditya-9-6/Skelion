"""
Comprehensive Unit Tests for Epoll-Based Adaptive Rate-Limiting Mesh.
"""

import socket
import time

from skelion_agent.sre.ratelimit import (
    AdaptiveRateLimitConfig,
    TokenBucketMesh,
    EpollAdaptiveMeshRateLimiter,
)


def test_token_bucket_mesh_basic():
    bucket = TokenBucketMesh(capacity=10.0, refill_rate=5.0, initial_tokens=10.0)
    assert bucket.consume(5.0) is True
    assert bucket.tokens < 6.0
    assert bucket.consume(10.0) is False


def test_token_bucket_refill():
    bucket = TokenBucketMesh(capacity=10.0, refill_rate=100.0, initial_tokens=0.0)
    time.sleep(0.05)
    assert bucket.consume(1.0) is True


def test_adaptive_rate_limiter_lifecycle():
    config = AdaptiveRateLimitConfig(
        base_rate=50.0,
        max_rate=100.0,
        min_rate=5.0,
        burst_capacity=20.0,
        backpressure_trigger_ratio=0.7,
        shedding_trigger_ratio=0.9,
    )
    limiter = EpollAdaptiveMeshRateLimiter(config)
    limiter.start()
    try:
        metrics = limiter.get_metrics()
        assert metrics["current_load"] == 0.0
        assert metrics["backpressure_active"] is False
        assert limiter.acquire(1.0) is True
    finally:
        limiter.stop()


def test_adaptive_rate_limiter_telemetry_and_shedding():
    config = AdaptiveRateLimitConfig(
        base_rate=50.0,
        max_rate=100.0,
        min_rate=5.0,
        burst_capacity=10.0,
        backpressure_trigger_ratio=0.7,
        shedding_trigger_ratio=0.9,
    )
    limiter = EpollAdaptiveMeshRateLimiter(config)
    limiter.start()
    try:
        # Normal load
        limiter.ingest_telemetry(0.3)
        assert limiter.acquire(1.0) is True

        # Critical load / shedding
        limiter.ingest_telemetry(0.95)
        metrics = limiter.get_metrics()
        assert metrics["shedding_active"] is True
        assert metrics["backpressure_active"] is True
        assert limiter.acquire(1.0) is False
    finally:
        limiter.stop()


def test_backpressure_propagation_sockets():
    config = AdaptiveRateLimitConfig()
    limiter = EpollAdaptiveMeshRateLimiter(config)
    limiter.start()

    server_sock, client_sock = socket.socketpair()
    try:
        limiter.register_peer_socket(server_sock)
        # Trigger high load to cause backpressure signal send
        limiter.ingest_telemetry(0.90)

        client_sock.settimeout(0.5)
        data = client_sock.recv(1024)
        assert len(data) > 0
        limiter.unregister_peer_socket(server_sock)
    finally:
        server_sock.close()
        client_sock.close()
        limiter.stop()
