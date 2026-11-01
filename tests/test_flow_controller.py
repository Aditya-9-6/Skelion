import pytest
from skelion_agent.flow_controller import VectorClockFlowController


def test_flow_controller_initialization():
    controller = VectorClockFlowController(node_id="node-1", high_watermark=100, low_watermark=40)
    assert controller.node_id == "node-1"
    assert controller.high_watermark == 100
    assert controller.low_watermark == 40
    stats = controller.get_stats()
    assert stats["passed_count"] == 0
    assert stats["throttled_count"] == 0
    assert stats["dropped_count"] == 0


def test_vector_clock_increment_and_sync():
    controller = VectorClockFlowController(node_id="node-1")
    assert controller.increment() == 1
    assert controller.increment() == 2
    
    controller.update_clock({"node-2": 5, "node-1": 1})
    clock = controller.get_clock()
    assert clock["node-1"] == 2
    assert clock["node-2"] == 5


def test_congestion_gradient_calculation():
    controller = VectorClockFlowController(node_id="node-1", high_watermark=100, low_watermark=0)
    assert controller.calculate_congestion_gradient(0) == 0.0
    assert controller.calculate_congestion_gradient(50) == 0.5
    assert controller.calculate_congestion_gradient(100) == 1.0
    assert controller.calculate_congestion_gradient(150) == 1.0


def test_evaluate_payload_severity_protection():
    controller = VectorClockFlowController(node_id="node-1", high_watermark=50, low_watermark=10)
    
    # Even at extreme queue depth, critical/high incidents pass
    assert controller.evaluate_payload(priority="CRITICAL", queue_depth=200) == "PASS"
    assert controller.evaluate_payload(priority="HIGH", queue_depth=200) == "PASS"
    assert controller.evaluate_payload(priority="INCIDENT", queue_depth=200) == "PASS"


def test_evaluate_payload_throttling_and_dropping():
    controller = VectorClockFlowController(node_id="node-1", high_watermark=100, low_watermark=0)
    
    # Low queue depth -> PASS
    assert controller.evaluate_payload(priority="LOW", queue_depth=20) == "PASS"
    
    # Moderate-high queue depth (> 50) -> THROTTLE
    assert controller.evaluate_payload(priority="LOW", queue_depth=60) == "THROTTLE"
    
    # Max congestion queue depth (>= 100) -> DROP
    assert controller.evaluate_payload(priority="LOW", queue_depth=100) == "DROP"
    
    stats = controller.get_stats()
    assert stats["passed_count"] >= 1
    assert stats["throttled_count"] >= 1
    assert stats["dropped_count"] >= 1
