import asyncio
import pytest
import time
from skelion_agent.core.lock_manager import DistributedLockManager


@pytest.mark.asyncio
async def test_lock_acquisition_and_release():
    manager = DistributedLockManager(node_id="node-1", default_lease_ttl=2.0)
    await manager.start()

    try:
        success, token, owner = await manager.acquire_lock("infra-resource-1")
        assert success is True
        assert token > 0
        assert owner == "node-1"

        status = manager.get_lock_status("infra-resource-1")
        assert status is not None
        assert status["owner_id"] == "node-1"
        assert status["fencing_token"] == token

        # Release lock
        released = await manager.release_lock("infra-resource-1", token)
        assert released is True
        assert manager.get_lock_status("infra-resource-1") is None
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_concurrent_lock_contention():
    manager_1 = DistributedLockManager(node_id="node-1", default_lease_ttl=2.0)
    manager_2 = DistributedLockManager(node_id="node-2", default_lease_ttl=2.0)

    await manager_1.start()
    await manager_2.start()

    try:
        # Node 1 acquires lock
        success_1, token_1, owner_1 = await manager_1.acquire_lock("shared-db")
        assert success_1 is True

        # Node 2 tries to acquire same lock while held
        success_2, token_2, owner_2 = await manager_2.acquire_lock("shared-db")
        assert success_2 is False
        assert owner_2 == "node-1"

        # Node 2 tries with stale token release -> should fail
        released_stale = await manager_2.release_lock("shared-db", token_1)
        assert released_stale is False

        # Node 1 releases correctly
        released = await manager_1.release_lock("shared-db", token_1)
        assert released is True

        # Now Node 2 should successfully acquire
        success_2_retry, token_2_retry, owner_2_retry = await manager_2.acquire_lock("shared-db")
        assert success_2_retry is True
        assert owner_2_retry == "node-2"
        assert token_2_retry > token_1
        await manager_2.release_lock("shared-db", token_2_retry)
    finally:
        await manager_1.stop()
        await manager_2.stop()


@pytest.mark.asyncio
async def test_lease_expiration_and_heartbeat():
    # Short TTL for quick expiration test
    manager = DistributedLockManager(node_id="node-1", default_lease_ttl=0.5)
    await manager.start(heartbeat_interval=0.1)

    try:
        success, token, _ = await manager.acquire_lock("ephemeral-job")
        assert success is True

        # Wait for heartbeats to keep renewing lease
        await asyncio.sleep(1.0)
        status = manager.get_lock_status("ephemeral-job")
        assert status is not None
        assert status["is_expired"] is False
    finally:
        await manager.stop()
