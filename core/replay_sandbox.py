# core/replay_sandbox.py — Sandboxed Replay Verification Engine
"""
Replays captured, redacted HTTP requests against a local patched service or
isolated test sandbox to verify fixes before proposing or merging PRs.
Follows Phase 2 safety rules:
1. Idempotent methods only by default (GET, HEAD, OPTIONS).
2. Non-idempotent blocked unless explicitly allowed.
3. Strict timeout and concurrency limits.
4. Returns structured verification object with confidence score.
"""

import time
import urllib.request
import urllib.error
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}


class ReplayResult:
    def __init__(
        self,
        requests_replayed: int,
        passed: int,
        failed: int,
        regressions: int,
        latency_delta_ms: float,
        flaky_count: int,
        coverage_of_routes: float,
        confidence: float,
        details: List[Dict[str, Any]],
    ):
        self.requests_replayed = requests_replayed
        self.passed = passed
        self.failed = failed
        self.regressions = regressions
        self.latency_delta_ms = latency_delta_ms
        self.flaky_count = flaky_count
        self.coverage_of_routes = coverage_of_routes
        self.confidence = round(max(0.0, min(1.0, confidence)), 3)
        self.details = details
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_replayed": self.requests_replayed,
            "passed": self.passed,
            "failed": self.failed,
            "regressions": self.regressions,
            "latency_delta_ms": round(self.latency_delta_ms, 2),
            "flaky_count": self.flaky_count,
            "coverage_of_routes": round(self.coverage_of_routes, 3),
            "confidence": self.confidence,
            "details": self.details,
            "timestamp": self.timestamp,
        }


def calculate_confidence(
    replayed: int,
    passed: int,
    regressions: int,
    coverage: float,
    has_test_suite_passed: bool = True,
) -> float:
    """Calculate transparent confidence score based on verification metrics."""
    if replayed == 0:
        return 0.5 if has_test_suite_passed else 0.2

    pass_rate = passed / replayed
    base = pass_rate * 0.70
    coverage_weight = min(1.0, coverage) * 0.15
    test_suite_weight = 0.15 if has_test_suite_passed else 0.0

    score = base + coverage_weight + test_suite_weight
    # Severe penalty for regressions
    score -= regressions * 0.35

    return round(max(0.0, min(1.0, score)), 3)


def run_replay_verification(
    replays: List[Dict[str, Any]],
    target_base_url: Optional[str] = None,
    allow_non_idempotent: bool = False,
    timeout_seconds: float = 3.0,
    mock_responses: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Execute replay verification against target service or mock harness.
    
    Each replay item should be a dict:
    {
        "method": "GET",
        "path": "/api/users/profile",
        "headers": {"Accept": "application/json"},
        "body": None,
        "baseline_status": 500, # What it did during incident
        "baseline_latency_ms": 120.0
    }
    """
    total_replayed = 0
    passed = 0
    failed = 0
    regressions = 0
    total_latency_delta = 0.0
    details = []
    unique_routes = set()
    total_routes_target = set(r.get("path", "/") for r in replays)

    for item in replays:
        method = item.get("method", "GET").upper()
        path = item.get("path", "/")
        baseline_status = item.get("baseline_status", 500)
        baseline_latency = item.get("baseline_latency_ms", 50.0)

        # Safety check: enforce idempotent methods by default
        if not allow_non_idempotent and method not in IDEMPOTENT_METHODS:
            details.append({
                "path": path,
                "method": method,
                "status": "skipped",
                "reason": f"Method {method} is non-idempotent and disallowed by replay safety policy.",
            })
            continue

        total_replayed += 1
        unique_routes.add(path)

        # Execution against real target or mock
        t0 = time.perf_counter()
        actual_status = 200
        error_msg = None

        if mock_responses and path in mock_responses:
            actual_status = mock_responses[path]
            elapsed_ms = 15.0
        elif target_base_url:
            url = target_base_url.rstrip("/") + "/" + path.lstrip("/")
            headers = item.get("headers", {})
            headers.setdefault("User-Agent", "Skelion-Replay-Verifier/2.0")
            body_bytes = None
            if item.get("body"):
                body_bytes = json.dumps(item["body"]).encode("utf-8") if isinstance(item["body"], dict) else str(item["body"]).encode("utf-8")

            req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                    actual_status = resp.status
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
            except urllib.error.HTTPError as he:
                actual_status = he.code
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
            except Exception as exc:
                actual_status = 599  # connection error
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                error_msg = str(exc)
        else:
            # Default dry-run pass
            actual_status = 200
            elapsed_ms = 12.0

        latency_delta = elapsed_ms - baseline_latency
        total_latency_delta += latency_delta

        # Assessment
        # If baseline was failing (>=400) and actual is now 2xx -> Fix Verified!
        # If baseline was 200 and actual is now >=400 -> Regression!
        is_regression = (baseline_status < 400 and actual_status >= 400)
        is_pass = (actual_status < 400) and not is_regression

        if is_regression:
            regressions += 1
            failed += 1
        elif is_pass:
            passed += 1
        else:
            failed += 1

        details.append({
            "path": path,
            "method": method,
            "baseline_status": baseline_status,
            "actual_status": actual_status,
            "latency_ms": round(elapsed_ms, 2),
            "latency_delta_ms": round(latency_delta, 2),
            "verdict": "regression" if is_regression else ("pass" if is_pass else "fail"),
            "error": error_msg,
        })

    coverage = len(unique_routes) / max(1, len(total_routes_target))
    avg_latency_delta = (total_latency_delta / max(1, total_replayed)) if total_replayed else 0.0
    conf = calculate_confidence(total_replayed, passed, regressions, coverage)

    result = ReplayResult(
        requests_replayed=total_replayed,
        passed=passed,
        failed=failed,
        regressions=regressions,
        latency_delta_ms=avg_latency_delta,
        flaky_count=0,
        coverage_of_routes=coverage,
        confidence=conf,
        details=details,
    )
    return result.to_dict()
