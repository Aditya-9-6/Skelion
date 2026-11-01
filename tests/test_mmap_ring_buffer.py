import pytest
import time
import threading
from skelion_agent.core.mmap_ring_buffer import MMapRingBuffer


def test_mmap_ring_buffer_basic():
    buffer_name = f"test_basic_{int(time.time() * 1000)}"
    ring = MMapRingBuffer(name=buffer_name, capacity=8, slot_size=64, create=True)
    try:
        assert ring.push(b"incident-telemetry-1") is True
        assert ring.push(b"incident-telemetry-2") is True

        item1 = ring.pop()
        assert item1 == b"incident-telemetry-1"

        item2 = ring.pop()
        assert item2 == b"incident-telemetry-2"

        assert ring.pop() is None
    finally:
        ring.close()


def test_mmap_ring_buffer_capacity_bounds():
    buffer_name = f"test_bounds_{int(time.time() * 1000)}"
    ring = MMapRingBuffer(name=buffer_name, capacity=4, slot_size=32, create=True)
    try:
        # Fill capacity exactly
        for i in range(4):
            assert ring.push(f"msg-{i}".encode()) is True

        # Buffer should be full
        assert ring.push(b"overflow") is False

        # Pop one and push another
        assert ring.pop() == b"msg-0"
        assert ring.push(b"msg-4") is True

        # Drain remaining
        assert ring.pop() == b"msg-1"
        assert ring.pop() == b"msg-2"
        assert ring.pop() == b"msg-3"
        assert ring.pop() == b"msg-4"
        assert ring.pop() is None
    finally:
        ring.close()


def test_mmap_ring_buffer_concurrency():
    buffer_name = f"test_concurrency_{int(time.time() * 1000)}"
    ring = MMapRingBuffer(name=buffer_name, capacity=256, slot_size=64, create=True)
    
    iterations = 500
    produced = []
    consumed = []

    def producer():
        for i in range(iterations):
            data = f"telemetry-{i}".encode()
            while not ring.push(data):
                time.sleep(0.0001)
                
    def consumer():
        count = 0
        while count < iterations:
            item = ring.pop()
            if item:
                consumed.append(item)
                count += 1
            else:
                time.sleep(0.0001)

    try:
        t_prod = threading.Thread(target=producer)
        t_cons = threading.Thread(target=consumer)

        t_cons.start()
        t_prod.start()

        t_prod.join(timeout=5.0)
        t_cons.join(timeout=5.0)

        assert len(consumed) == iterations
    finally:
        ring.close()
