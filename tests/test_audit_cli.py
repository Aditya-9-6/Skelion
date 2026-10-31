# tests/test_audit_cli.py — Audit CLI Acceptance Tests

import os
import json
import tempfile
from core.audit_cli import parse_log_line, analyze_logs, run_audit


def test_parse_nginx_and_jsonl():
    # 1. Nginx combined line
    nginx_line = '127.0.0.1 - - [24/Oct/2026:14:00:00 +0000] "GET /api/v1/orders/123/status HTTP/1.1" 200 1024 "-" "Mozilla/5.0" 0.045'
    parsed = parse_log_line(nginx_line)
    assert parsed is not None
    assert parsed["method"] == "GET"
    assert parsed["route"] == "/api/v1/orders/:id/status"
    assert parsed["status"] == 200
    assert parsed["latency_ms"] == 45.0

    # 2. JSONL line
    json_line = json.dumps(
        {
            "timestamp": "2026-10-24T14:00:00Z",
            "method": "POST",
            "path": "/v1/chat",
            "status": 502,
            "latency_ms": 120.5,
            "error": "Upstream connection failed",
        }
    )
    parsed2 = parse_log_line(json_line)
    assert parsed2 is not None
    assert parsed2["method"] == "POST"
    assert parsed2["status"] == 502
    assert parsed2["latency_ms"] == 120.5


def test_analyzers_find_planted_issues():
    records = [
        # Silent 200 failure (HTTP 200 but error body)
        {
            "method": "POST",
            "raw_path": "/api/checkout",
            "route": "/api/checkout",
            "status": 200,
            "latency_ms": 30.0,
            "body": '{"status":"failed","error":"Payment card expired"}',
        },
        {
            "method": "POST",
            "raw_path": "/api/checkout",
            "route": "/api/checkout",
            "status": 200,
            "latency_ms": 25.0,
            "body": '{"error":"Insufficient funds"}',
        },
        # 5xx Outage
        {
            "method": "GET",
            "raw_path": "/api/products",
            "route": "/api/products",
            "status": 500,
            "latency_ms": 100.0,
            "body": "Internal Server Error",
        },
        # 429 LLM Storm
        {
            "method": "POST",
            "raw_path": "/v1/agent",
            "route": "/v1/agent",
            "status": 429,
            "latency_ms": 15.0,
            "body": "Rate limit exceeded",
        },
        # Normal healthy traffic
        {
            "method": "GET",
            "raw_path": "/healthz",
            "route": "/healthz",
            "status": 200,
            "latency_ms": 5.0,
            "body": "ok",
        },
    ]

    metrics = analyze_logs(records)
    assert metrics["total_requests"] == 5
    assert len(metrics["issues"]) >= 3

    categories = [i["category"] for i in metrics["issues"]]
    assert "silent_failure" in categories
    assert "server_crash" in categories
    assert "rate_limit_storm" in categories


def test_end_to_end_audit_cli_generates_reports():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "access.log")
        out_dir = os.path.join(tmpdir, "report")

        # Write sample access log
        sample_logs = [
            '{"path": "/v1/telemetry", "status": 200, "body": "success", "latency_ms": 10}\n',
            '{"path": "/v1/checkout", "status": 200, "body": "{\\"error\\": \\"Database deadlock\\"}", "latency_ms": 50}\n',
            '{"path": "/v1/search", "status": 500, "body": "Traceback: ZeroDivisionError", "latency_ms": 600}\n',
        ]
        with open(log_file, "w") as f:
            f.writelines(sample_logs)

        result = run_audit(log_file, project_name="Test Service", output_dir=out_dir)
        assert result["status"] == "success"
        assert result["requests_analyzed"] == 3
        assert result["issues_count"] >= 1

        # Check that report files exist
        assert os.path.exists(result["html_report"])
        assert os.path.exists(result["findings_json"])

        # Check content
        with open(result["findings_json"]) as f:
            findings = json.load(f)
            assert findings["total_requests"] == 3
