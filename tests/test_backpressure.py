import asyncio
import pytest
from skelion_agent.sre.backpressure import (
    AdaptiveBackpressureController,
    BackpressureConfig,
    BackpressureState,
)


@pytest.mark.asyncio
async def test_backpressure_normal_flow():
    config = BackpressureConfig(capacity=10.0, leak_rate_per_sec=5.0)
    controller = AdaptiveBackpressureController(config)

    # Small payload should be admitted
    admitted = await controller.acquire(cost=2.0, loop_latency_ms=10.0)
    assert admitted is True

    metrics = await controller.get_metrics()
    assert metrics["total_admitted"] == 1
    assert metrics["total_shed"] == 0
    assert metrics["state"] == BackpressureState.NORMAL.value


@pytest.mark.asyncio
async def test_backpressure_shedding_behavior():
    config = BackpressureConfig(capacity=5.0, leak_rate_per_sec=0.1)
    controller = AdaptiveBackpressureController(config)

    # Fill up the bucket beyond capacity
    admitted1 = await controller.acquire(cost=4.0, loop_latency_ms=10.0)
    assert admitted1 is True

    # Next request exceeds capacity -> should shed
    admitted2 = await controller.acquire(cost=3.0, loop_latency_ms=10.0)
    assert admitted2 is False

    metrics = await controller.get_metrics()
    assert metrics["total_shed"] == 1
    assert metrics["state"] == BackpressureState.SHEDDING.value


@pytest.mark.asyncio
async def test_leaky_bucket_drain():
    config = BackpressureConfig(capacity=10.0, leak_rate_per_sec=50.0)
    controller = AdaptiveBackpressureController(config)

    # Acquire almost full capacity
    assert await controller.acquire(cost=9.0, loop_latency_ms=10.0) is True

    # Wait briefly to allow leak
    await asyncio.sleep(0.05)

    # Bucket should have drained, allowing new admission
    assert await controller.acquire(cost=2.0, loop_latency_ms=10.0) is True


@pytest.mark.asyncio
async def test_event_loop_latency_penalty():
    config = BackpressureConfig(capacity=10.0, leak_rate_per_sec=1.0)
    controller = AdaptiveBackpressureController(config)

    # High loop latency (>50ms) adds penalty cost
    admitted = await controller.acquire(cost=2.0, loop_latency_ms=150.0)
    metrics = await controller.get_metrics()
    assert metrics["last_loop_latency_ms"] == 150.0
    # Level includes cost 2.0 + (150-50)/10 = 12.0 -> exceeds capacity 10.0 -> shed
    assert admitted is False
