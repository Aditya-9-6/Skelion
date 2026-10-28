# tests/test_replay_sandbox.py — Replay Sandbox Verification Tests

import pytest
from core.replay_sandbox import run_replay_verification, calculate_confidence, IDEMPOTENT_METHODS


def test_idempotent_method_enforcement():
    replays = [
        {"method": "GET", "path": "/api/safe", "baseline_status": 500},
        {"method": "POST", "path": "/api/dangerous", "baseline_status": 500},
        {"method": "DELETE", "path": "/api/delete", "baseline_status": 500},
    ]

    # Without allow_non_idempotent, POST and DELETE must be skipped
    res = run_replay_verification(replays, allow_non_idempotent=False)
    assert res["requests_replayed"] == 1
    assert len(res["details"]) == 3
    skipped = [d for d in res["details"] if d.get("status") == "skipped"]
    assert len(skipped) == 2


def test_replay_verification_pass_and_regression():
    replays = [
        {"method": "GET", "path": "/api/recovered", "baseline_status": 500},
        {"method": "GET", "path": "/api/broken_now", "baseline_status": 200},
    ]

    mock_responses = {
        "/api/recovered": 200,   # Baseline was 500, now 200 -> Pass!
        "/api/broken_now": 500,  # Baseline was 200, now 500 -> Regression!
    }

    res = run_replay_verification(replays, mock_responses=mock_responses)
    assert res["requests_replayed"] == 2
    assert res["passed"] == 1
    assert res["regressions"] == 1
    assert res["failed"] == 1


def test_confidence_score_calculation():
    # 10 replayed, all passed, no regressions, 100% route coverage
    c_high = calculate_confidence(10, 10, 0, 1.0, True)
    assert c_high >= 0.85

    # Regressions should penalize score heavily
    c_regressed = calculate_confidence(10, 8, 2, 1.0, True)
    assert c_regressed < c_high
