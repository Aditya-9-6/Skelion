from skelion_agent.sre.load_shedder import AdaptiveLoadShedder
from skelion_agent.sre.reactor import EpollReactorMesh


def test_load_shedder_basic_flow():
    shedder = AdaptiveLoadShedder(target_latency_sec=0.1, max_concurrent_limit=2)

    # Initially should not shed
    assert not shedder.should_shed()

    # Acquire first slot
    assert shedder.acquire() is True
    # Acquire second slot
    assert shedder.acquire() is True

    # Third slot should be shed because max_concurrent_limit is reached
    assert shedder.acquire() is False

    metrics = shedder.get_metrics()
    assert metrics["active_requests"] == 2
    assert metrics["shed_count"] == 1

    # Release slots
    shedder.release(0.05)
    shedder.release(0.05)

    metrics_after = shedder.get_metrics()
    assert metrics_after["active_requests"] == 0
    assert metrics_after["request_count"] == 2


def test_littles_law_saturation():
    shedder = AdaptiveLoadShedder(target_latency_sec=0.01, max_concurrent_limit=10)

    # Simulate high active requests with high rolling latency
    for _ in range(5):
        shedder.acquire()

    # Artificially inject high latency to trigger Little's Law backpressure
    shedder._rolling_latency = 0.5

    assert shedder.should_shed() is True


def test_epoll_reactor_integration():
    reactor = EpollReactorMesh()
    assert reactor.evaluate_inbound() is True
    reactor.complete_request(0.01)
    metrics = reactor.load_shedder.get_metrics()
    assert metrics["request_count"] == 1
    reactor.close()
