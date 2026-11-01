import threading
import time
import pytest
from skelion_agent.rcu_mesh import RCURoutingTable, RCUEpochTracker


def test_rcu_basic_crud():
    mesh = RCURoutingTable()
    assert mesh.lookup("agent_a") is None

    mesh.update_route("agent_a", {"endpoint": "http://localhost:8001", "weight": 10})
    assert mesh.lookup("agent_a") == {"endpoint": "http://localhost:8001", "weight": 10}

    mesh.update_route("agent_a", {"endpoint": "http://localhost:8001", "weight": 20})
    assert mesh.lookup("agent_a") == {"endpoint": "http://localhost:8001", "weight": 20}

    assert mesh.remove_route("agent_a") is True
    assert mesh.lookup("agent_a") is None
    assert mesh.remove_route("non_existent") is False


def test_concurrent_rcu_readers_writers():
    mesh = RCURoutingTable()
    stop_event = threading.Event()

    # Populate initial routes
    for i in range(50):
        mesh.update_route(f"agent_{i}", {"id": i})

    def reader_thread():
        while not stop_event.is_set():
            for i in range(50):
                val = mesh.lookup(f"agent_{i}")
                if val is not None:
                    assert "id" in val

    def writer_thread():
        counter = 100
        while not stop_event.is_set():
            target = f"agent_{counter % 50}"
            mesh.update_route(target, {"id": counter})
            counter += 1
            time.sleep(0.001)

    readers = [threading.Thread(target=reader_thread) for _ in range(8)]
    writers = [threading.Thread(target=writer_thread) for _ in range(2)]

    for t in readers + writers:
        t.start()

    time.sleep(0.5)
    stop_event.set()

    for t in readers + writers:
        t.join()

    assert len(mesh.get_all_routes()) == 50
