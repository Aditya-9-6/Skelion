import pytest
from skelion_agent.cardinality_guard import CardinalityGuard


def test_cardinality_guard_basic():
    guard = CardinalityGuard(capacity=100, error_rate=0.01)
    
    # First time seeing metric should be admitted (True)
    assert guard.check_and_add("http_requests_total", {"method": "GET", "status": "200"}) is True
    
    # Seeing exact same metric/labels should return True (already present)
    assert guard.check_and_add("http_requests_total", {"method": "GET", "status": "200"}) is True
    
    stats = guard.stats
    assert stats["item_count"] == 1
    assert stats["admitted_count"] == 2


def test_cardinality_guard_capacity_bound():
    # Small capacity guard
    guard = CardinalityGuard(capacity=5, error_rate=0.01)
    
    # Add 5 distinct items
    for i in range(5):
        res = guard.check_and_add("agent_inference_latency", {"agent_id": f"agent-{i}"})
        assert res is True
        
    # 6th distinct item should trigger the capacity guard and be dropped/guarded
    res_excess = guard.check_and_add("agent_inference_latency", {"agent_id": "agent-excess"})
    assert res_excess is False
    
    stats = guard.stats
    assert stats["dropped_count"] == 1


def test_cardinality_guard_reset():
    guard = CardinalityGuard(capacity=10, error_rate=0.01)
    assert guard.check_and_add("metric_a", {"env": "prod"}) is True
    assert guard.stats["item_count"] == 1
    
    guard.reset()
    assert guard.stats["item_count"] == 0
    assert guard.stats["dropped_count"] == 0
    assert guard.stats["admitted_count"] == 0
