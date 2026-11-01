import time
import pytest
from skelion_agent.scheduler import WorkStealingQueue, NUMAAwareScheduler


def test_work_stealing_queue_basic():
    queue = WorkStealingQueue(capacity=4)
    assert len(queue) == 0

    assert queue.push("task1") is True
    assert queue.push("task2") is True
    assert len(queue) == 2

    assert queue.pop() == "task2"
    assert len(queue) == 1

    assert queue.pop() == "task1"
    assert len(queue) == 0
    assert queue.pop() is None


def test_work_stealing_queue_capacity_power_of_two():
    queue = WorkStealingQueue(capacity=5)
    assert queue.capacity == 8
    assert queue.mask == 7


def test_work_stealing_queue_overflow():
    queue = WorkStealingQueue(capacity=2)
    assert queue.push(1) is True
    assert queue.push(2) is True
    assert queue.push(3) is False


def test_work_stealing_mechanism():
    q1 = WorkStealingQueue(capacity=16)
    q2 = WorkStealingQueue(capacity=16)

    assert q1.push("t1") is True
    assert q1.push("t2") is True

    # q2 steals from q1
    stolen = q1.steal()
    assert stolen == "t1"
    assert len(q1) == 1

    stolen_second = q1.steal()
    assert stolen_second == "t2"
    assert len(q1) == 0
    assert q1.steal() is None


def test_numa_aware_scheduler_execution():
    scheduler = NUMAAwareScheduler(num_workers=4, numa_nodes=2, queue_capacity=64)
    
    # Submit tasks load-balanced
    for i in range(10):
        assert scheduler.schedule_load_balanced(f"remediate-{i}") is True

    scheduler.start(task_handler=lambda t: f"handled-{t}")
    time.sleep(0.1)
    scheduler.stop()

    assert len(scheduler._results) == 10
    assert "handled-remediate-0" in scheduler._results
