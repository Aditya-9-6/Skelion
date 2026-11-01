import threading
import time
import pytest
from skelion_agent.core.hazard import HazardPointerManager


class DummyResource:
    def __init__(self, val: int):
        self.val = val
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


def test_hazard_pointer_basic_acquire_release():
    manager = HazardPointerManager(max_hazards_per_thread=2)
    res = DummyResource(42)

    assert manager.acquire(res, 0) is res
    manager.release(0)

    deleted = []
    manager.retire(res, lambda r: (r.destroy(), deleted.append(r)))
    manager.force_reclaim_all()

    assert res.destroyed is True
    assert res in deleted


def test_hazard_pointer_protection_against_premature_deletion():
    manager = HazardPointerManager(scan_threshold=1)
    res = DummyResource(100)

    # Acquire hazard pointer keeping it alive
    manager.acquire(res, 0)

    deleted = []
    manager.retire(res, lambda r: (r.destroy(), deleted.append(r)))

    # Attempt reclaim while hazard pointer is held
    manager.force_reclaim_all()
    assert res.destroyed is False
    assert res not in deleted

    # Release hazard pointer and re-reclaim
    manager.release(0)
    manager.force_reclaim_all()
    assert res.destroyed is True
    assert res in deleted


def test_concurrent_hazard_pointer_stress():
    manager = HazardPointerManager(scan_threshold=10)
    num_threads = 8
    iterations = 200
    errors = []

    shared_resources = [DummyResource(i) for i in range(50)]

    def worker_thread(thread_idx: int):
        try:
            for i in range(iterations):
                res = shared_resources[(thread_idx + i) % len(shared_resources)]
                manager.acquire(res, 0)
                # Simulate workload reading resource
                val = res.val
                if res.destroyed:
                    errors.append(f"Use-after-free detected for resource {val}!")
                time.sleep(0.0001)
                manager.release(0)

                if i % 10 == 0:
                    expired_res = DummyResource(999 + i)
                    manager.retire(expired_res, lambda r: r.destroy())
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    manager.force_reclaim_all()
    assert not errors, f"Concurrency errors or use-after-free detected: {errors}"
