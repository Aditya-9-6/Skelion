import threading
import time
import pytest
from skelion_agent.core.lcrq import LCRQ, HazardPointerTable, EpochReclaimer, LCRQNode


def test_lcrq_basic_operations():
    queue = LCRQ()
    assert queue.size == 0
    assert queue.dequeue() is None

    queue.enqueue("task_1")
    queue.enqueue("task_2")
    queue.enqueue("task_3")
    assert queue.size == 3

    assert queue.dequeue() == "task_1"
    assert queue.dequeue() == "task_2"
    assert queue.size == 1

    queue.enqueue("task_4")
    assert queue.size == 2

    assert queue.dequeue() == "task_3"
    assert queue.dequeue() == "task_4"
    assert queue.dequeue() is None
    assert queue.size == 0


def test_lcrq_concurrent_stress():
    queue = LCRQ(max_threads=32)
    num_threads = 16
    items_per_thread = 200

    def producer(start_idx: int):
        for i in range(items_per_thread):
            queue.enqueue(f"item_{start_idx}_{i}")

    consumed_items = []
    consumed_lock = threading.Lock()

    def consumer():
        while True:
            item = queue.dequeue()
            if item is not None:
                with consumed_lock:
                    consumed_items.append(item)
            else:
                # Check if all items produced and queue empty
                with consumed_lock:
                    if len(consumed_items) >= num_threads * items_per_thread:
                        break
                time.sleep(0.001)

    threads = []
    for t in range(num_threads):
        p = threading.Thread(target=producer, args=(t,))
        c = threading.Thread(target=consumer)
        threads.extend([p, c])

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=10.0)

    assert len(consumed_items) == num_threads * items_per_thread
    assert queue.size == 0


def test_hazard_pointer_and_reclaimer():
    table = HazardPointerTable()
    reclaimer = EpochReclaimer(table, threshold=2)
    
    node1 = LCRQNode("a")
    node2 = LCRQNode("b")

    table.protect(0, node1)
    assert table.is_protected(node1) is True
    assert table.is_protected(node2) is False

    reclaimer.retire(node1)
    reclaimer.retire(node2)
    
    # node1 is protected so should remain in reclaimer buffer
    assert node1 in reclaimer._retired

    table.clear(0)
    assert table.is_protected(node1) is False

    reclaimer.force_reclaim()
    assert node1.value is None
