import time
import pytest
from skelion_agent.bulkhead import EpollBulkheadMesh, BulkheadConfig


def test_bulkhead_concurrency_bounds():
    mesh = EpollBulkheadMesh(node_id="node-1")
    pool = "test-pool"
    mesh.register_pool(
        pool, BulkheadConfig(max_concurrent=2, queue_capacity=2, acquire_timeout=0.1)
    )

    assert mesh.acquire(pool) is True
    assert mesh.acquire(pool) is True
    # Third concurrent request should queue and time out if capacity is strict
    assert mesh.acquire(pool) is False

    mesh.release(pool)
    assert mesh.acquire(pool) is True
    mesh.release(pool)
    mesh.release(pool)
    mesh.close()


def test_bulkhead_lease_context_manager():
    mesh = EpollBulkheadMesh(node_id="node-1")
    pool = "ctx-pool"
    mesh.register_pool(pool, BulkheadConfig(max_concurrent=1, acquire_timeout=0.5))

    with mesh.lease(pool) as lease:
        assert lease.acquired is True
        with pytest.raises(TimeoutError):
            with mesh.lease(pool):
                pass

    mesh.close()


def test_leader_election_heartbeat():
    mesh = EpollBulkheadMesh(node_id="node-1")
    pool = "leader-pool"
    mesh.register_pool(pool, BulkheadConfig(leader_lease_timeout=0.2))

    assert mesh.heartbeat(pool, "node-1") is True
    assert mesh.get_leader(pool) == "node-1"

    # Node 2 tries to claim while lease is active
    assert mesh.heartbeat(pool, "node-2") is False
    assert mesh.get_leader(pool) == "node-1"

    # Wait for lease timeout
    time.sleep(0.3)
    assert mesh.heartbeat(pool, "node-2") is True
    assert mesh.get_leader(pool) == "node-2"

    mesh.close()
