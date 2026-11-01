import pytest
from skelion_agent.core.mpmc_ring import MPMCRingBuffer


def test_ring_buffer_init():
    ring = MPMCRingBuffer(capacity=4)
    assert len(ring) == 0

    with pytest.raises(ValueError):
        MPMCRingBuffer(capacity=3)


def test_ring_buffer_push_pop():
    ring = MPMCRingBuffer(capacity=4)
    assert ring.push("agent_1") is True
    assert ring.push("agent_2") is True
    assert len(ring) == 2

    assert ring.pop() == "agent_1"
    assert ring.pop() == "agent_2"
    assert ring.pop() is None
    assert len(ring) == 0


def test_ring_buffer_overflow():
    ring = MPMCRingBuffer(capacity=2)
    assert ring.push(1) is True
    assert ring.push(2) is True
    assert ring.push(3) is False
    assert len(ring) == 2

    assert ring.pop() == 1
    assert ring.push(3) is True
    assert len(ring) == 2
