import threading
import pytest
from skelion_agent.ring_buffer import MPMCRingBuffer, Cell
import ctypes


def test_cell_alignment():
    cell = Cell()
    assert ctypes.sizeof(cell) == 64


def test_ring_buffer_invalid_capacity():
    with pytest.raises(ValueError):
        MPMCRingBuffer(capacity=100)


def test_ring_buffer_basic_push_pop():
    buf = MPMCRingBuffer(capacity=4)
    assert len(buf) == 0

    assert buf.push("item1") is True
    assert buf.push("item2") is True
    assert len(buf) == 2

    success, item = buf.pop()
    assert success is True
    assert item == "item1"
    assert len(buf) == 1

    success, item = buf.pop()
    assert success is True
    assert item == "item2"
    assert len(buf) == 0

    success, item = buf.pop()
    assert success is False
    assert item is None


def test_ring_buffer_overflow():
    buf = MPMCRingBuffer(capacity=2)
    assert buf.push(1) is True
    assert buf.push(2) is True
    assert buf.push(3) is False


def test_concurrent_mpmc():
    capacity = 256
    buf = MPMCRingBuffer(capacity=capacity)
    num_items = 1000
    num_threads = 4

    def producer(start_val):
        for i in range(start_val, start_val + (num_items // num_threads)):
            while not buf.push(i):
                pass

    consumed_items = []
    consumed_lock = threading.Lock()

    def consumer():
        while len(consumed_items) < num_items:
            success, item = buf.pop()
            if success:
                with consumed_lock:
                    consumed_items.append(item)

    threads = []
    for t in range(num_threads):
        p = threading.Thread(target=producer, args=(t * (num_items // num_threads),))
        c = threading.Thread(target=consumer)
        threads.extend([p, c])

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    assert len(consumed_items) == num_items
    assert sorted(consumed_items) == list(range(num_items))
