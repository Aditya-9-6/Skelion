import concurrent.futures
import random
import time
import pytest

from skelion_agent.core.radix_router import RadixRouter


def test_radix_router_basic_insert_and_lookup():
    router = RadixRouter()
    router.insert("/metrics/cpu/usage", "cpu_handler")
    router.insert("/metrics/cpu/temperature", "temp_handler")
    router.insert("/metrics/memory/usage", "mem_handler")
    router.insert("/incidents/sev1", "sev1_handler")

    assert router.lookup("/metrics/cpu/usage") == "cpu_handler"
    assert router.lookup("/metrics/cpu/temperature") == "temp_handler"
    assert router.lookup("/metrics/memory/usage") == "mem_handler"
    assert router.lookup("/incidents/sev1") == "sev1_handler"
    assert router.lookup("/metrics/cpu") is None
    assert router.lookup("/nonexistent") is None


def test_radix_router_prefix_splitting():
    router = RadixRouter()
    router.insert("/api/v1/agents", "v1_agents")
    router.insert("/api/v1/clusters", "v1_clusters")
    router.insert("/api/v2/agents", "v2_agents")

    assert router.lookup("/api/v1/agents") == "v1_agents"
    assert router.lookup("/api/v1/clusters") == "v1_clusters"
    assert router.lookup("/api/v2/agents") == "v2_agents"
    assert router.lookup("/api/v1") is None


def test_radix_router_deletion():
    router = RadixRouter()
    router.insert("/telemetry/node/heartbeat", "heartbeat_handler")
    assert router.lookup("/telemetry/node/heartbeat") == "heartbeat_handler"

    assert router.delete("/telemetry/node/heartbeat") is True
    assert router.lookup("/telemetry/node/heartbeat") is None
    assert router.delete("/telemetry/node/nonexistent") is False


def test_radix_router_concurrent_stress():
    router = RadixRouter()
    # Pre-populate base paths
    for i in range(100):
        router.insert(f"/metric/{i}/rate", f"rate_{i}")

    errors = []

    def writer_worker(thread_id: int):
        try:
            for j in range(50):
                path = f"/metric/writer_{thread_id}/{j}"
                router.insert(path, f"val_{thread_id}_{j}")
        except Exception as e:
            errors.append(e)

    def reader_worker():
        try:
            for _ in range(200):
                idx = random.randint(0, 99)
                router.lookup(f"/metric/{idx}/rate")
        except Exception as e:
            errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(writer_worker, i) for i in range(4)
        ] + [
            executor.submit(reader_worker) for _ in range(4)
        ]
        concurrent.futures.wait(futures)

    assert len(errors) == 0
    # Verify sanity of lookups after concurrent updates
    assert router.lookup("/metric/10/rate") == "rate_10"
