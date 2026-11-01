import time
import pytest
from skelion_agent.core.journal import MmapJournal, JournalCorruptionError


@pytest.fixture
def temp_journal(tmp_path):
    path = str(tmp_path / "remediation.journal")
    journal = MmapJournal(path, capacity_bytes=8192)
    yield journal
    journal.close()


def test_journal_basic_append_and_replay(temp_journal):
    offset1 = temp_journal.append(
        "PLAYBOOK_STARTED", {"playbook_id": "pb-123", "target": "svc-auth"}
    )
    offset2 = temp_journal.append(
        "STEP_EXECUTED", {"step": "restart_container", "status": "success"}
    )

    assert offset1 >= MmapJournal.HEADER_SIZE
    assert offset2 > offset1

    records = temp_journal.replay()
    assert len(records) == 2
    assert records[0]["type"] == "PLAYBOOK_STARTED"
    assert records[0]["data"]["playbook_id"] == "pb-123"
    assert records[1]["type"] == "STEP_EXECUTED"
    assert records[1]["data"]["status"] == "success"


def test_journal_cold_boot_recovery(tmp_path):
    path = str(tmp_path / "cold_boot.journal")

    # Write entries with initial instance
    j1 = MmapJournal(path, capacity_bytes=8192)
    j1.append("INIT_STATE", {"state": "active"})
    j1.append("TRANSITION", {"from": "active", "to": "remediating"})
    j1.close()

    # Cold boot simulation under 5ms requirement
    start_time = time.perf_counter()
    j2 = MmapJournal(path, capacity_bytes=8192)
    records = j2.replay()
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert (
        elapsed_ms < 5.0
    ), f"Cold boot recovery took {elapsed_ms:.2f}ms (exceeded 5ms limit)"
    assert len(records) == 2
    assert records[1]["data"]["to"] == "remediating"
    j2.close()


def test_journal_corruption_detection(tmp_path):
    path = str(tmp_path / "corrupted.journal")
    j1 = MmapJournal(path, capacity_bytes=8192)
    j1.append("SAFE_RECORD", {"val": 42})
    j1.close()

    # Corrupt the payload inside the file directly
    with open(path, "r+b") as f:
        f.seek(MmapJournal.HEADER_SIZE + 4)  # Corrupt inside CRC/payload
        f.write(b"\xff\xff\xff\xff")

    with pytest.raises(JournalCorruptionError):
        MmapJournal(path, capacity_bytes=8192)


def test_journal_compaction_and_rotation(tmp_path):
    path = str(tmp_path / "compact.journal")
    # Small capacity to force rotation
    journal = MmapJournal(path, capacity_bytes=512)

    journal.append("EVENT_1", {"data": "A" * 50})
    journal.append("EVENT_2", {"data": "B" * 50})
    journal.append("EVENT_3", {"data": "C" * 50})

    records = journal.replay()
    assert len(records) == 3
    assert records[0]["type"] == "EVENT_1"
    assert records[2]["type"] == "EVENT_3"
    journal.close()
