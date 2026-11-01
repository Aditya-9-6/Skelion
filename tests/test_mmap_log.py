import os
import tempfile
from skelion_agent.storage.mmap_log import MMapAppendOnlyLog


def test_mmap_log_basic_append_and_read():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "audit_test.log")
        log = MMapAppendOnlyLog(log_path, segment_size=1024 * 1024)

        payload1 = b"incident_state_v1"
        payload2 = b"audit_remediation_event_v2"

        idx1 = log.append(payload1)
        idx2 = log.append(payload2)

        assert idx1 == 0
        assert idx2 == 1
        assert log.entry_count == 2

        ts1, len1, p1 = log.read_entry(0)
        ts2, len2, p2 = log.read_entry(1)

        assert p1 == payload1
        assert len1 == len(payload1)
        assert p2 == payload2
        assert len2 == len(payload2)

        log.fsync()
        log.close()


def test_mmap_log_iteration():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "audit_iter.log")
        log = MMapAppendOnlyLog(log_path, segment_size=1024 * 1024)

        messages = [b"msg_one", b"msg_two", b"msg_three"]
        for m in messages:
            log.append(m)

        entries = list(log.iter_entries())
        assert len(entries) == 3
        for i, (_, _, payload) in enumerate(entries):
            assert payload == messages[i]

        log.close()


def test_mmap_log_persistence_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "audit_persist.log")
        log1 = MMapAppendOnlyLog(log_path, segment_size=1024 * 1024)
        log1.append(b"persistent_event")
        log1.close()

        # Reopen same file
        log2 = MMapAppendOnlyLog(log_path, segment_size=1024 * 1024)
        assert log2.entry_count == 1
        _, _, payload = log2.read_entry(0)
        assert payload == b"persistent_event"
        log2.close()
