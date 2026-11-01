import pytest
import threading
import time
import socket

from skelion_agent.flow_classifier import ConcurrentRadixFlowClassifier, RadixLeafNode


def test_radix_leaf_node_cas():
    node = RadixLeafNode(prefix="test", value="initial", is_terminal=True)
    assert node.compare_and_swap_value("initial", "updated") is True
    assert node.value == "updated"
    assert node.version == 1
    assert node.compare_and_swap_value("wrong_expected", "other") is False
    assert node.value == "updated"


def test_flow_classifier_insert_and_classify():
    classifier = ConcurrentRadixFlowClassifier()
    classifier.insert_flow("telemetry.metrics.cpu", "CPU_AGENT")
    classifier.insert_flow("telemetry.metrics.memory", "MEM_AGENT")
    classifier.insert_flow("telemetry.logs.error", "ERR_AGENT")

    assert classifier.classify("telemetry.metrics.cpu") == "CPU_AGENT"
    assert classifier.classify("telemetry.metrics.memory") == "MEM_AGENT"
    assert classifier.classify("telemetry.logs.error") == "ERR_AGENT"
    assert classifier.classify("telemetry.metrics.disk") is None
    assert classifier.classify("unknown") is None


def test_flow_classifier_path_compression_and_splitting():
    classifier = ConcurrentRadixFlowClassifier()
    classifier.insert_flow("api.v1.users", "USERS_V1")
    classifier.insert_flow("api.v1.users.profile", "USER_PROFILE_V1")
    classifier.insert_flow(
        "api.v1.organizations", "ORGS_V1"
    )  # Should split 'users'

    assert classifier.classify("api.v1.users") == "USERS_V1"
    assert classifier.classify("api.v1.users.profile") == "USER_PROFILE_V1"
    assert classifier.classify("api.v1.organizations") == "ORGS_V1"


def test_concurrent_flow_insertions():
    classifier = ConcurrentRadixFlowClassifier()

    def worker(prefix: str, count: int):
        for i in range(count):
            classifier.insert_flow(f"{prefix}.flow_{i}", f"VAL_{i}")

    threads = [
        threading.Thread(target=worker, args=("region_a", 50)),
        threading.Thread(target=worker, args=("region_b", 50)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert classifier.classify("region_a.flow_10") == "VAL_10"
    assert classifier.classify("region_b.flow_49") == "VAL_49"


def test_epoll_telemetry_loop_lifecycle():
    classifier = ConcurrentRadixFlowClassifier(port=9234)
    classifier.insert_flow("ping", "pong")
    classifier.start_epoll_server()
    time.sleep(0.1)

    stats = classifier.get_stats()
    assert stats["running"] is True

    classifier.stop_epoll_server()
    assert classifier.get_stats()["running"] is False
