import concurrent.futures
import pytest
from skelion_agent.core.ring_buffer import MPMCRingBuffer


def test_ring_buffer_init_validation():
    with pytest.raises(ValueError):
        MPMCRingBuffer(capacity=100)  # Not a power of two
    
    buf = MPMCRingBuffer(capacity=16)
    assert len(buf) == 0


def test_single_producer_single_consumer():
    buf = MPMCRingBuffer(capacity=4)
    
    assert buf.push("alpha") is True
    assert buf.push("beta") is True
    assert buf.push("gamma") is True
    assert buf.push("delta") is True
    assert buf.push("overflow") is False  # Full

    success, item = buf.pop()
    assert success is True
    assert item == "alpha"

    success, item = buf.pop()
    assert success is True
    assert item == "beta"

    assert buf.push("epsilon") is True

    _, item = buf.pop()
    assert item == "gamma"
    _, item = buf.pop()
    assert item == "delta"
    _, item = buf.pop()
    assert item == "epsilon"

    success, item = buf.pop()
    assert success is False
    assert item is None


def test_concurrent_mpmc_stress():
    capacity = 256
    buf = MPMCRingBuffer(capacity=capacity)
    num_items = 1000
    num_threads = 8

    def producer(start_val: int):
        for i in range(start_val, start_val + (num_items // num_threads)):
            while not buf.push(i):
                pass

    results = []
    results_lock = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)

    def consumer():
        popped = []
        while len(popped) < (num_items // num_threads):
            success, val = buf.pop()
            if success:
                popped.append(val)
        return popped

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads * 2) as executor:
        prod_futures = [
            executor.submit(producer, i * (num_items // num_threads))
            for i in range(num_threads)
        ]
        cons_futures = [
            executor.submit(consumer)
            for _ in range(num_threads)
        ]

        concurrent.futures.wait(prod_futures)
        all_consumed = []
        for f in cons_futures:
            all_consumed.extend(f.result())

    assert len(all_consumed) == num_items
    assert sorted(all_consumed) == list(range(num_items))
