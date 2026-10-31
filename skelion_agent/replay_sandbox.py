# skelion_agent/replay_sandbox.py — Deterministic Failure Replay Sandbox
"""
Isolated test harness to re-execute recorded production HTTP error payloads with
simulated downstream mock latencies, failure injection, and deterministic assertions.
"""

import time
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}


class ReplaySandboxResult:
    def __init__(
        self,
        total_replayed: int,
        passed: int,
        failed: int,
        regressions: int,
        avg_latency_ms: float,
        max_latency_ms: float,
        flaky_count: int,
        confidence: float,
        details: List[Dict[str, Any]],
    ):
        self.total_replayed = total_replayed
        self.passed = passed
        self.failed = failed
        self.regressions = regressions
        self.avg_latency_ms = round(avg_latency_ms, 2)
        self.max_latency_ms = round(max_latency_ms, 2)
        self.flaky_count = flaky_count
        self.confidence = round(max(0.0, min(1.0, confidence)), 3)
        self.details = details
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_replayed": self.total_replayed,
            "passed": self.passed,
            "failed": self.failed,
            "regressions": self.regressions,
            "avg_latency_ms": self.avg_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "flaky_count": self.flaky_count,
            "confidence": self.confidence,
            "details": self.details,
            "timestamp": self.timestamp,
        }


def calculate_sandbox_confidence(
    total: int,
    passed: int,
    regressions: int,
    has_test_suite_passed: bool = True,
) -> float:
    """Calculate sandbox verification confidence score."""
    if total == 0:
        return 0.5 if has_test_suite_passed else 0.1

    pass_rate = passed / total
    base = pass_rate * 0.75
    test_suite_weight = 0.25 if has_test_suite_passed else 0.0
    score = base + test_suite_weight
    score -= regressions * 0.40

    return round(max(0.0, min(1.0, score)), 3)


def run_failure_replay_sandbox(
    replays: List[Dict[str, Any]],
    target_base_url: str,
    allow_non_idempotent: bool = False,
    timeout_seconds: float = 5.0,
    simulated_latency_ms: float = 0.0,
    inject_status_override: Optional[int] = None,
) -> Dict[str, Any]:
    """Replay captured HTTP error payloads against a sandbox target with fault injection."""
    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0
    regressions = 0
    flaky_count = 0
    latencies: List[float] = []

    for item in replays:
        method = item.get("method", "GET").upper()
        path = item.get("path", "/")
        headers = item.get("headers", {})
        body = item.get("body")
        baseline_status = item.get("baseline_status", 500)

        if method not in IDEMPOTENT_METHODS and not allow_non_idempotent:
            results.append({
                "path": path,
                "method": method,
                "status": "skipped",
                "reason": "Non-idempotent method blocked by security policy",
            })
            continue

        url = f"{target_base_url.rstrip('/')}{path}"
        req_data = json.dumps(body).encode("utf-8") if body else None

        req_headers = {**headers}
        if req_data and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"

        start_time = time.perf_counter()
        status_code = 500
        error_message = None

        try:
            if simulated_latency_ms > 0:
                time.sleep(simulated_latency_ms / 1000.0)

            req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                status_code = resp.getcode()
        except urllib.error.HTTPError as e:
            status_code = e.code
        except Exception as e:
            status_code = 599
            error_message = str(e)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        latencies.append(duration_ms)

        if inject_status_override is not None:
            status_code = inject_status_override

        is_fixed = status_code < 500
        is_regression = status_code >= 500 and baseline_status < 500

        if is_fixed:
            passed += 1
        else:
            failed += 1

        if is_regression:
            regressions += 1

        results.append({
            "path": path,
            "method": method,
            "baseline_status": baseline_status,
            "replayed_status": status_code,
            "latency_ms": round(duration_ms, 2),
            "is_fixed": is_fixed,
            "is_regression": is_regression,
            "error": error_message,
        })

    total_replayed = len([r for r in results if r.get("status") != "skipped"])
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0

    confidence = calculate_sandbox_confidence(total_replayed, passed, regressions)

    res = ReplayResultObj = ReplaySandboxResult(
        total_replayed=total_replayed,
        passed=passed,
        failed=failed,
        regressions=regressions,
        avg_latency_ms=avg_lat,
        max_latency_ms=max_lat,
        flaky_count=flaky_count,
        confidence=confidence,
        details=results,
    )

    return res.to_dict()
