import pytest
import ctypes
import time
from skelion_agent.core.ebpf_ring import EBPFRingBuffer, EBPFPerfEvent


def test_ebpf_ring_buffer_happy_path():
    ring_name = f"test_ring_{int(time.time() * 1000)}"
    ring = EBPFRingBuffer(name=ring_name, capacity=16, create=True)

    try:
        event = EBPFPerfEvent(
            timestamp=123456789,
            pid=4242,
            cpu=2,
            event_type=1,  # TCP Retransmit
            saddr=0xC0A80101,
            daddr=0xC0A80102,
            sport=443,
            dport=55555,
            payload_len=1024,
        )

        assert ring.push_event(event) is True

        stats = ring.stats()
        assert stats["depth"] == 1
        assert stats["is_empty"] is False

        popped = ring.pop_event()
        assert popped is not None
        assert popped.timestamp == 123456789
        assert popped.pid == 4242
        assert popped.cpu == 2
        assert popped.event_type == 1
        assert popped.sport == 443
        assert popped.dport == 55555

        stats_after = ring.stats()
        assert stats_after["depth"] == 0
        assert stats_after["is_empty"] is True
    finally:
        ring.close()


def test_ebpf_ring_buffer_overflow():
    ring_name = f"test_overflow_{int(time.time() * 1000)}"
    capacity = 4
    ring = EBPFRingBuffer(name=ring_name, capacity=capacity, create=True)

    try:
        for i in range(capacity):
            evt = EBPFPerfEvent(timestamp=i, pid=1000 + i, cpu=0, event_type=2, saddr=0, daddr=0, sport=0, dport=0, payload_len=0)
            assert ring.push_event(evt) is True

        # Next push should fail as buffer is full
        overflow_evt = EBPFPerfEvent(timestamp=999, pid=9999, cpu=0, event_type=2, saddr=0, daddr=0, sport=0, dport=0, payload_len=0)
        assert ring.push_event(overflow_evt) is False

        # Pop one and push should succeed again
        popped = ring.pop_event()
        assert popped is not None
        assert popped.timestamp == 0

        assert ring.push_event(overflow_evt) is True
    finally:
        ring.close()


def test_ebpf_ring_poll_batch():
    ring_name = f"test_poll_{int(time.time() * 1000)}"
    ring = EBPFRingBuffer(name=ring_name, capacity=10, create=True)

    try:
        for i in range(5):
            evt = EBPFPerfEvent(timestamp=100 + i, pid=2000 + i, cpu=1, event_type=1, saddr=1, daddr=2, sport=80, dport=8080, payload_len=64)
            ring.push_event(evt)

        events = list(ring.poll_events(max_batch=3))
        assert len(events) == 3
        assert events[0].timestamp == 100
        assert events[2].timestamp == 102

        remaining = list(ring.poll_events(max_batch=10))
        assert len(remaining) == 2
        assert remaining[0].timestamp == 103
        assert remaining[1].timestamp == 104
    finally:
        ring.close()
