import asyncio
import pytest
import queue
from skelion_agent.core.queue import MPMCLockFreeQueue


@pytest.mark.asyncio
async def test_queue_initialization_and_capacity():
    q = MPMCLockFreeQueue(capacity=16)
    assert q.capacity == 16
    assert q.empty() is True
    assert q.full() is False
    assert q.qsize() == 0


@pytest.mark.asyncio
async def test_queue_power_of_two_adjustment():
    q = MPMCLockFreeQueue(capacity=10)
    # 10 should round up to 16
    assert q.capacity == 16


@pytest.mark.asyncio
async def test_nowait_operations():
    q = MPMCLockFreeQueue(capacity=4)
    assert q.put_nowait("item1") is True
    assert q.put_nowait("item2") is True
    assert q.qsize() == 2
    assert q.empty() is False

    assert q.get_nowait() == "item1"
    assert q.get_nowait() == "item2"
    assert q.empty() is True

    with pytest.raises(queue.Empty):
        q.get_nowait()


@pytest.mark.asyncio
async def test_queue_capacity_limit():
    q = MPMCLockFreeQueue(capacity=2)
    assert q.put_nowait(1) is True
    assert q.put_nowait(2) is True
    assert q.full() is True
    assert q.put_nowait(3) is False

    assert q.get_nowait() == 1
    assert q.full() is False
    assert q.put_nowait(3) is True


@pytest.mark.asyncio
async def test_async_put_and_get():
    q = MPMCLockFreeQueue(capacity=4)
    success = await q.put("async_item", timeout=1.0)
    assert success is True
    assert q.qsize() == 1

    item = await q.get(timeout=1.0)
    assert item == "async_item"
    assert q.empty() is True


@pytest.mark.asyncio
async def test_concurrent_mpmc_stress():
    q = MPMCLockFreeQueue(capacity=256)
    num_producers = 4
    items_per_producer = 100
    total_items = num_producers * items_per_producer

    async def producer(pid: int):
        for i in range(items_per_producer):
            val = pid * 1000 + i
            while not q.put_nowait(val):
                await asyncio.sleep(0.0001)

    async def consumer(results: list):
        while len(results) < total_items:
            try:
                item = q.get_nowait()
                results.append(item)
            except queue.Empty:
                await asyncio.sleep(0.0001)

    results = []
    prod_tasks = [asyncio.create_task(producer(p)) for p in range(num_producers)]
    cons_tasks = [asyncio.create_task(consumer(results)) for _ in range(2)]

    await asyncio.gather(*prod_tasks)
    await asyncio.gather(*cons_tasks)

    assert len(results) == total_items
    assert len(set(results)) == total_items
