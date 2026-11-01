import time
import threading
from skelion_agent.core.shm_ring import SharedMemoryRingBuffer


def test_shm_ring_basic_push_pop():
    ring_name = "test_ring_basic"
    buffer = SharedMemoryRingBuffer(
        name=ring_name, capacity=4, slot_size=32, create=True
    )
    try:
        assert len(buffer) == 0

        # Push items
        assert buffer.push(b"hello") is True
        assert buffer.push(b"world") is True
        assert len(buffer) == 2

        # Pop items
        assert buffer.pop() == b"hello"
        assert buffer.pop() == b"world"
        assert len(buffer) == 0
        assert buffer.pop() is None
    finally:
        buffer.close()
        buffer.unlink()


def test_shm_ring_overflow_and_wrap():
    ring_name = "test_ring_overflow"
    buffer = SharedMemoryRingBuffer(
        name=ring_name, capacity=2, slot_size=16, create=True
    )
    try:
        assert buffer.push(b"msg1") is True
        assert buffer.push(b"msg2") is True
        # Buffer should be full now (capacity=2)
        assert buffer.push(b"msg3") is False

        # Pop one and push another (testing wrap around)
        assert buffer.pop() == b"msg1"
        assert buffer.push(b"msg3") is True

        assert buffer.pop() == b"msg2"
        assert buffer.pop() == b"msg3"
        assert buffer.pop() is None
    finally:
        buffer.close()
        buffer.unlink()


def test_shm_ring_concurrent_producer_consumer():
    ring_name = "test_ring_concurrent"
    buffer = SharedMemoryRingBuffer(
        name=ring_name, capacity=64, slot_size=64, create=True
    )

    num_messages = 100
    consumed = []

    def producer():
        for i in range(num_messages):
            msg = f"metric_{i}".encode()
            while not buffer.push(msg):
                time.sleep(0.0001)

    def consumer():
        count = 0
        while count < num_messages:
            item = buffer.pop()
            if item:
                consumed.append(item)
                count += 1
            else:
                time.sleep(0.0001)

    try:
        t_prod = threading.Thread(target=producer)
        t_cons = threading.Thread(target=consumer)

        t_prod.start()
        t_cons.start()

        t_prod.join(timeout=5.0)
        t_cons.join(timeout=5.0)

        assert len(consumed) == num_messages
        for i in range(num_messages):
            assert consumed[i] == f"metric_{i}".encode()
    finally:
        buffer.close()
        buffer.unlink()
