import pytest
from skelion_agent.proxy.differ import ResponseDiffer


def test_response_differ_identical():
    prod = {
        "status_code": 200,
        "headers": {"content-type": "application/json", "server": "nginx"},
        "body": '{"result": 42, "items": [1, 2, 3]}'
    }
    sandbox = {
        "status_code": 200,
        "headers": {"content-type": "application/json", "server": "envoy"},
        "body": '{"result": 42, "items": [1, 2, 3]}'
    }

    report = ResponseDiffer.diff_responses(prod, sandbox)
    assert report["status_matched"] is True
    assert report["has_regression"] is False
    assert len(report["body_diffs"]) == 0


def test_response_differ_status_mismatch():
    prod = {"status_code": 200, "headers": {}, "body": '{"ok": true}'}
    sandbox = {"status_code": 500, "headers": {}, "body": '{"error": "internal"}'}

    report = ResponseDiffer.diff_responses(prod, sandbox)
    assert report["status_matched"] is False
    assert report["has_regression"] is True
    assert report["production_status"] == 200
    assert report["sandbox_status"] == 500


def test_response_differ_structural_body_mismatch():
    prod = {
        "status_code": 200,
        "headers": {},
        "body": '{"user": "alice", "roles": ["admin", "user"], "score": 95.5}'
    }
    sandbox = {
        "status_code": 200,
        "headers": {},
        "body": '{"user": "alice", "roles": ["admin"], "score": 80.0, "extra": true}'
    }

    report = ResponseDiffer.diff_responses(prod, sandbox)
    assert report["status_matched"] is True
    assert report["has_regression"] is True
    assert len(report["body_diffs"]) > 0

    issues = [d.get("issue") or d.get("path") for d in report["body_diffs"]]
    assert any("roles" in str(i) or "score" in str(i) or "extra" in str(i) for i in issues)
