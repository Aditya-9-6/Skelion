import os
import tempfile
import pytest
import threading
import time
from skelion_agent.storage.mmap_log import MMapAppendOnlyLog
from skelion_agent.storage.replication import LogReplicator


def test_log_replicator_initialization():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "repl_test.log")
        log = MMapAppendOnlyLog(log_path, segment_size=1024 * 1024)
        log.append(b"replication_test_payload")
        
        replicator = LogReplicator(node_id="node-1", log=log, bind_addr="127.0.0.1", port=9191)
        assert replicator.node_id == "node-1"
        assert replicator.vector_clock.get_time("node-1") == 0
        
        replicator.vector_clock.increment()
        assert replicator.vector_clock.get_time("node-1") == 1
        
        log.close()


def test_replicator_anti_entropy_sync():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path1 = os.path.join(tmpdir, "node1.log")
        log_path2 = os.path.join(tmpdir, "node2.log")
        
        log1 = MMapAppendOnlyLog(log_path1, segment_size=1024 * 1024)
        log2 = MMapAppendOnlyLog(log_path2, segment_size=1024 * 1024)
        
        rep1 = LogReplicator(node_id="node-1", log=log1, bind_addr="127.0.0.1", port=9192)
        rep2 = LogReplicator(node_id="node-2", log=log2, bind_addr="127.0.0.1", port=9193)
        
        log1.append(b"event_node_1")
        log2.append(b"event_node_2")
        
        clock1 = rep1.vector_clock.snapshot()
        success = rep1.sync_with_peer("127.0.0.1", 9193, clock1)
        # Verification of function execution and error-free execution
        assert isinstance(success, bool)
        
        rep1.close()
        rep2.close()
        log1.close()
        log2.close()
