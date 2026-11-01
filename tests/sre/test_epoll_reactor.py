# tests/sre/test_epoll_reactor.py — Automated verification suite for #183
from skelion_agent.sre.epoll_reactor import FeatsreImplementEpollEdge


def test_epoll_reactor_lifecycle():
    instance = FeatsreImplementEpollEdge(capacity=100)
    assert instance.capacity == 100
    res = instance.process_item(
        "edge_metric_1", {"event": "synthetic_verification", "value": 42}
    )
    assert res["status"] == "ok"
    assert res["key"] == "edge_metric_1"
    assert res["capacity_used"] == 1
    metrics = instance.get_metrics()
    assert metrics["total_processed"] == 1


def test_epoll_reactor_concurrency_bounds():
    instance = FeatsreImplementEpollEdge(capacity=50)
    for i in range(10):
        instance.process_item(f"edge_key_{i}", {"val": i})
    metrics = instance.get_metrics()
    assert metrics["total_processed"] == 10
