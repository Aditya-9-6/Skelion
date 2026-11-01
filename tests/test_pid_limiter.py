import time
import pytest
from skelion_agent.sre.pid_limiter import AdaptivePIDLimiter
from skelion_agent.sre.epoll_loop import EpollTelemetryLoop

def test_pid_limiter_happy_path():
    limiter = AdaptivePIDLimiter(target_latency=0.05, min_concurrency=10, max_concurrency=1000)
    initial_limit = limiter.get_limit()
    assert initial_limit == 1000

    # Simulate low latency and low queue depth -> limit stays high or adapts stably
    new_limit = limiter.update(current_latency=0.02, queue_depth=20, dropped=False)
    assert new_limit >= 10
    assert new_limit <= 1000

    stats = limiter.get_stats()
    assert stats["success_count"] == 1
    assert stats["drop_count"] == 0

def test_pid_limiter_high_latency_throttling():
    limiter = AdaptivePIDLimiter(target_latency=0.05, min_concurrency=10, max_concurrency=1000)
    # Simulate high latency and high queue depth -> should throttle / reduce limit
    limit1 = limiter.update(current_latency=0.20, queue_depth=800, dropped=True)
    limit2 = limiter.update(current_latency=0.35, queue_depth=1200, dropped=True)
    
    assert limit2 < limit1
    stats = limiter.get_stats()
    assert stats["drop_count"] == 2

def test_epoll_telemetry_loop_lifecycle():
    limiter = AdaptivePIDLimiter()
    loop = EpollTelemetryLoop(pid_limiter=limiter, host="127.0.0.1", port=0)
    loop.start()
    assert loop.get_status()["running"] is True
    loop.stop()
    assert loop.get_status()["running"] is False
