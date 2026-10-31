"""Comprehensive deep unit tests for Deterministic Failure Replay Sandbox."""

import pytest
from skelion_agent.replay_sandbox import (
    run_failure_replay_sandbox,
    calculate_sandbox_confidence,
    ReplaySandboxResult,
)


def test_calculate_sandbox_confidence():
    score_empty = calculate_sandbox_confidence(0, 0, 0, True)
    assert score_empty == 0.75

    score_perfect = calculate_sandbox_confidence(10, 10, 0, True)
    assert score_perfect == 1.0

    score_regression = calculate_sandbox_confidence(10, 8, 2, True)
    assert score_regression < 0.5


def test_replay_sandbox_non_idempotent_blocking():
    replays = [
        {
            "method": "POST",
            "path": "/api/mutate",
            "baseline_status": 500,
        }
    ]
    result = run_failure_replay_sandbox(
        replays=replays,
        target_base_url="http://localhost:9999",
        allow_non_idempotent=False,
    )
    assert result["total_replayed"] == 0
    assert result["details"][0]["status"] == "skipped"


def test_replay_sandbox_result_to_dict():
    res = ReplaySandboxResult(
        total_replayed=5,
        passed=4,
        failed=1,
        regressions=0,
        avg_latency_ms=45.234,
        max_latency_ms=80.123,
        flaky_count=0,
        confidence=0.95,
        details=[{"path": "/test"}],
    )
    data = res.to_dict()
    assert data["total_replayed"] == 5
    assert data["passed"] == 4
    assert data["avg_latency_ms"] == 45.23
    assert data["confidence"] == 0.95
    assert "timestamp" in data
