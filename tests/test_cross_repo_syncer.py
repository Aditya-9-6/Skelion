# tests/test_cross_repo_syncer.py — Test Suite for Cross-Repository Upstream Auto-Sync Engine
import pytest
from unittest.mock import patch

from skelion_agent.cross_repo_syncer import CrossRepoSyncer


@pytest.fixture
def temp_syncer(tmp_path):
    syncer = CrossRepoSyncer(workspace_root=tmp_path)
    return syncer


def test_load_and_save_sync_state(temp_syncer):
    state = temp_syncer.load_state()
    assert "devproxy" in state
    assert "gossipmesh" in state
    assert state["devproxy"]["status"] == "UNSYNCED"

    temp_syncer.record_history(
        "devproxy", "TEST_EVENT", "abc1234", "SUCCESS", {"info": "test"}
    )
    reloaded = temp_syncer.load_state()
    assert len(reloaded.get("history", [])) == 1
    assert reloaded["history"][0]["sha"] == "abc1234"


def test_check_updates_detection(temp_syncer):
    with patch.object(temp_syncer, "get_upstream_head_sha") as mock_head:
        mock_head.side_effect = (
            lambda k: "sha_devproxy_new" if k == "devproxy" else "sha_gossipmesh_same"
        )
        temp_syncer.state["devproxy"]["last_synced_sha"] = "sha_devproxy_old"
        temp_syncer.state["gossipmesh"]["last_synced_sha"] = "sha_gossipmesh_same"

        updates = temp_syncer.check_updates()
        assert updates["devproxy"]["update_available"] is True
        assert updates["devproxy"]["upstream_head"] == "sha_devproxy_new"
        assert updates["gossipmesh"]["update_available"] is False


def test_direct_merge_on_clean_sync(temp_syncer):
    # Mock clean git environment and successful direct merge
    with patch.object(
        temp_syncer,
        "get_upstream_head_sha",
        return_value="c6e1958ec3a6d841a056e0b9702be311bc569ec1",
    ), patch.object(
        temp_syncer, "copy_mapped_files", return_value=["pkg/proxy/test.go"]
    ), patch("skelion_agent.cross_repo_syncer.run_cmd") as mock_run:
        # git diff/status returns staged changes with no conflicts (code=0, out="M pkg/proxy/test.go")
        def run_cmd_mock(cmd, cwd=None):
            if "status" in cmd:
                return (0, "M  pkg/proxy/test.go", "")
            if "diff" in cmd:
                return (0, "pkg/proxy/test.go | 2 +-", "")
            return (0, "", "")

        mock_run.side_effect = run_cmd_mock

        res = temp_syncer.sync_repository("devproxy", force=True)
        assert res["ok"] is True
        assert res["action"] == "DIRECT_MERGE"
        assert res["status"] == "MERGED"
        assert temp_syncer.state["devproxy"]["status"] == "SYNCED"


def test_pr_creation_on_conflict(temp_syncer):
    # Mock conflict detected (e.g. UU status indicating unmerged conflict or syntax break)
    with patch.object(
        temp_syncer, "get_upstream_head_sha", return_value="divergent_sha_9999"
    ), patch.object(
        temp_syncer, "copy_mapped_files", return_value=["gossipmesh/p2p/node.py"]
    ), patch("skelion_agent.cross_repo_syncer.run_cmd") as mock_run:

        def run_cmd_mock(cmd, cwd=None):
            if "status" in cmd:
                return (0, "UU gossipmesh/p2p/node.py", "")  # Unmerged conflict marker
            if "pr" in cmd and "create" in cmd:
                return (0, "https://github.com/Aditya-9-6/Skelion/pull/185", "")
            return (0, "", "")

        mock_run.side_effect = run_cmd_mock

        res = temp_syncer.sync_repository("gossipmesh", force=True)
        assert res["ok"] is True
        assert res["action"] == "PR_OPENED"
        assert res["status"] == "CONFLICT_NEEDS_REVIEW"
        assert "pull/185" in res["pr_url"]
        assert temp_syncer.state["gossipmesh"]["status"] == "CONFLICT_PR_OPENED"
