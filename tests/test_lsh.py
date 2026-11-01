import pytest
from skelion_agent.core.lsh import LSHIndex

def test_lsh_basic_clustering():
    lsh = LSHIndex(num_perm=64, threshold=0.5)
    
    log1 = "2023-10-01T12:00:00Z ERROR Database connection failed to host 192.168.1.50"
    log2 = "2023-10-01T12:01:05Z ERROR Database connection failed to host 192.168.1.55"
    log3 = "2023-10-01T12:02:10Z INFO User login successful for user_id=9921"
    
    lsh.add("log_1", log1)
    lsh.add("log_2", log2)
    lsh.add("log_3", log3)
    
    # Query similar to log1/log2
    query_line = "ERROR Database connection failed to host 192.168.1.99"
    results = lsh.query(query_line, top_k=2)
    
    assert len(results) > 0
    matched_ids = [r[0] for r in results]
    assert "log_1" in matched_ids or "log_2" in matched_ids
    assert "log_3" not in matched_ids

def test_lsh_empty_and_edge_cases():
    lsh = LSHIndex(num_perm=32, threshold=0.1)
    lsh.add("empty_1", "")
    lsh.add("special_1", "!@#$%^&*()")
    
    res = lsh.query("random query log line")
    assert isinstance(res, list)

def test_batch_fingerprint():
    lsh = LSHIndex(num_perm=32)
    batch = {
        "l1": "CPU usage high on node-01",
        "l2": "Memory limit exceeded on worker-02"
    }
    fingerprints = lsh.batch_fingerprint(batch)
    assert "l1" in fingerprints
    assert "l2" in fingerprints
    assert len(fingerprints["l1"]) == 32
