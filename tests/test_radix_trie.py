import concurrent.futures
import pytest
from skelion_agent.radix_trie import ConcurrentRadixTrie


def test_radix_basic_insert_and_search():
    trie = ConcurrentRadixTrie()
    trie.insert("sre.incident.auth", "auth_error")
    trie.insert("sre.incident.db", "db_timeout")
    trie.insert("sre.metric.cpu", "high_cpu")

    assert trie.search("sre.incident.auth") == "auth_error"
    assert trie.search("sre.incident.db") == "db_timeout"
    assert trie.search("sre.metric.cpu") == "high_cpu"
    assert trie.search("sre.missing") is None
    assert trie.size == 3


def test_radix_prefix_splitting():
    trie = ConcurrentRadixTrie()
    trie.insert("telemetry.error.500", "server_error")
    trie.insert("telemetry.error.404", "not_found")
    trie.insert("telemetry.metric", "metrics_root")

    assert trie.search("telemetry.error.500") == "server_error"
    assert trie.search("telemetry.error.404") == "not_found"
    assert trie.search("telemetry.metric") == "metrics_root"
    assert trie.size == 3


def test_radix_prefix_search():
    trie = ConcurrentRadixTrie()
    trie.insert("agent.us-west.sre1", "val1")
    trie.insert("agent.us-west.sre2", "val2")
    trie.insert("agent.eu-central.sre1", "val3")

    us_west_results = trie.prefix_search("agent.us-west.")
    assert len(us_west_results) == 2
    paths = {item[0] for item in us_west_results}
    assert paths == {"agent.us-west.sre1", "agent.us-west.sre2"}


def test_concurrent_radix_operations():
    trie = ConcurrentRadixTrie()

    def worker(worker_id: int):
        for i in range(100):
            key = f"node.{worker_id}.metric.{i}"
            trie.insert(key, f"val-{worker_id}-{i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, wid) for wid in range(8)]
        concurrent.futures.wait(futures)

    assert trie.size == 800
    assert trie.search("node.3.metric.42") == "val-3-42"
    assert trie.search("nonexistent") is None
