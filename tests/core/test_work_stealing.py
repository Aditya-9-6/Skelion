import concurrent.futures
import time
import pytest
from skelion_agent.core.work_stealing import WorkStealingQueue


def test_queue_initialization():
    queue = WorkStealingQueue(capacity=16)
    assert queue.capacity == 16
    assert len(queue) == 0


def test_push_and_pop_sequential():
    queue = WorkStealingQueue(capacity=4)
    assert queue.push("task1") is True
    assert queue.push("task2") is True
    assert len(queue) == 2

    assert queue.pop() == "task2"
    assert queue.pop() == "task1"
    assert queue.pop() is None
    assert len(queue) == 0


def test_queue_capacity_overflow():
    queue = WorkStealingQueue(capacity=2)
    assert queue.push(1) is True
    assert queue.push(2) is True
    assert queue.push(3) is False  # Full


def test_concurrent_push_and_steal():
    queue = WorkStealingQueue(capacity=1024)
    num_tasks = 200

    for i in range(num_tasks):
        assert queue.push(i) is True

    stolen_tasks = []
    lock = concurrent.futures.thread.threading.Lock()

    def worker():
        while True:
            task = queue.steal()
            if task is not None:
                with lock:
                    stolen_tasks.append(task)
            else:
                if len(queue) == 0 and sum(1 for _ in range(3)) == 3:
                    # Check if done
                    break
            time.sleep(0.001)

    # Spawn multiple thief threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker) for _ in range(4)]
        concurrent.futures.wait(futures, timeout=2.0)

    # Verify all tasks were eventually stolen or popped
    # Drain remaining via pop
    while True:
        t = queue.pop()
        if t is None:
            break
        stolen_tasks.append(t)

    assert len(set(stolen_tasks)) == num_tasks
    assert set(stolen_tasks) == set(range(num_tasks))
