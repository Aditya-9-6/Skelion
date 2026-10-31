import pytest
from skelion_agent.anomaly import WelfordOnlineStats, SlidingZScoreFilter


def test_welford_stats():
    stats = WelfordOnlineStats()
    assert stats.count == 0
    assert stats.mean == 0.0

    data = [10.0, 12.0, 23.0, 23.0, 16.0, 23.0, 21.0, 16.0]
    for val in data:
        stats.update(val)

    assert stats.count == len(data)
    assert pytest.approx(stats.mean, 0.01) == 18.0
    assert stats.standard_deviation > 0

    stats.reset()
    assert stats.count == 0
    assert stats.mean == 0.0


def test_sliding_z_score_filter_normal():
    detector = SlidingZScoreFilter(window_size=20, threshold=3.0)

    # Feed stable baseline data
    for _ in range(15):
        is_anomaly, z = detector.add(100.0)
        assert not is_anomaly


def test_sliding_z_score_filter_anomaly():
    detector = SlidingZScoreFilter(window_size=30, threshold=3.0)

    # Establish baseline
    for _ in range(25):
        detector.add(50.0)

    # Introduce a massive latency spike outlier
    is_anomaly, z = detector.add(500.0)
    assert is_anomaly
    assert z > 3.0


def test_sliding_window_eviction():
    detector = SlidingZScoreFilter(window_size=10, threshold=2.0)

    # Fill window with high values
    for _ in range(10):
        detector.add(100.0)

    # Shift baseline down completely
    for _ in range(10):
        detector.add(10.0)

    stats = detector.get_window_stats()
    assert stats["mean"] == 10.0
    assert stats["std_dev"] == 0.0
