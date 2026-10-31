import pytest
from skelion_agent.core.shm_ring import SharedMemoryRingBuffer


def_ring_name = "test_telemetry_ring_ipc"


def test_shm_ring_basic_operations():
    with SharedMemoryRingBuffer(
        name=def_ring_name, capacity=4, slot_size=64, create=True
    ) as ring:
        # Test push and pop happy path
        assert ring.push(b"metric_event_1") is True
        assert ring.push(b"metric_event_2") is True

        assert ring.pop() == b"metric_event_1"
        assert ring.pop() == b"metric_event_2"
        assert ring.pop() is None


def test_shm_ring_boundary_conditions():
    with SharedMemoryRingBuffer(
        name=def_ring_name + "_bounds", capacity=2, slot_size=32, create=True
    ) as ring:
        assert ring.push(b"a") is True
        assert ring.push(b"b") is True
        # Buffer is now full (capacity 2)
        assert ring.push(b"c") is False

        assert ring.pop() == b"a"
        # Now space is available
        assert ring.push(b"c") is True
        assert ring.pop() == b"b"
        assert ring.pop() == b"c"
        assert ring.pop() is None


def test_shm_ring_payload_size_validation():
    with SharedMemoryRingBuffer(
        name=def_ring_name + "_size", capacity=2, slot_size=16, create=True
    ) as ring:
        with pytest.raises(ValueError):
            ring.push(b"this payload is way too long for the slot size")
