from skelion_agent.ipc.shm_ring import SharedMemoryRingBuffer


def test_shm_ring_push_pop():
    ring = SharedMemoryRingBuffer(
        name="test_telemetry", capacity=16, slot_size=128, create=True
    )
    try:
        assert ring.push(b"metric_cpu_99") is True
        assert ring.push(b"metric_mem_42") is True

        val1 = ring.pop()
        assert val1 == b"metric_cpu_99"

        val2 = ring.pop()
        assert val2 == b"metric_mem_42"

        assert ring.pop() is None
    finally:
        ring.close()
        ring.unlink()


def test_shm_ring_overflow():
    ring = SharedMemoryRingBuffer(
        name="test_overflow", capacity=2, slot_size=64, create=True
    )
    try:
        assert ring.push(b"data_1") is True
        assert ring.push(b"data_2") is True
        # Buffer is capacity 2, should be full now
        assert ring.push(b"data_3") is False

        assert ring.pop() == b"data_1"
        assert ring.push(b"data_3") is True
    finally:
        ring.close()
        ring.unlink()
