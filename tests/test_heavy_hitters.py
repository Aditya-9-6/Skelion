import pytest
from skelion_agent.telemetry.heavy_hitters import HeavyHitters

def test_heavy_hitters_basic():
    hh = HeavyHitters(capacity=3)
    hh.add("error_500", 10)
    hh.add("error_404", 5)
    hh.add("info_200", 100)
    hh.add("warn_429", 2)

    # Capacity is 3, so warn_429 or error_404 might be evicted depending on arrival order, but top items persist
    est_200, err_200 = hh.query("info_200")
    assert est_200 == 100
    assert err_200 == 0

    est_500, err_500 = hh.query("error_500")
    assert est_500 == 10

    hitters = hh.get_heavy_hitters(threshold_fraction=0.05)
    items = [h[0] for h in hitters]
    assert "info_200" in items
    assert "error_500" in items

def test_heavy_hitters_skewed_stream():
    hh = HeavyHitters(capacity=5)
    # Stream with extreme skew: 'dominant' appears 1000 times, others appear once
    for _ in range(1000):
        hh.add("dominant")
    for i in range(100):
        hh.add(f"item_{i}")

    est, err = hh.query("dominant")
    assert est == 1000
    assert err == 0

    hitters = hh.get_heavy_hitters(threshold_fraction=0.1)
    assert len(hitters) >= 1
    assert hitters[0][0] == "dominant"
    assert hitters[0][1] == 1000

def test_heavy_hitters_invalid_capacity():
    with pytest.raises(ValueError):
        HeavyHitters(capacity=0)
    with pytest.raises(ValueError):
        HeavyHitters(capacity=-5)

def test_heavy_hitters_reset():
    hh = HeavyHitters(capacity=10)
    hh.add("test", 50)
    assert hh.query("test")[0] == 50
    hh.reset()
    assert hh.query("test")[0] is None
    assert hh._total_count == 0
