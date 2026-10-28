# tests/test_egress.py — Egress Schema & Data Leakage Security Tests

import pytest
from core.egress import sanitize_for_egress, validate_egress_payload, preview_llm_prompt


def test_egress_sanitizer_produces_compliant_payload():
    payload = sanitize_for_egress(
        project_id="proj_alpha",
        service_name="payment_svc",
        raw_path="/api/v1/orders/12345/checkout?ref=twitter",
        http_status=500,
        error_summary="SQL deadlock on balance update",
        latency_ms=180.0,
        severity="HIGH",
        count=3,
    )

    assert payload["project_id"] == "proj_alpha"
    assert payload["route_template"] == "/api/v1/orders/:id/checkout"
    assert payload["latency_bucket"] == "50-200ms"
    # Raw query string stripped completely
    assert "ref=twitter" not in payload["route_template"]
    # Error is hashed into a fingerprint
    assert len(payload["error_fingerprint"]) == 16


def test_disallowed_fields_fail_loudly():
    forbidden_payload = {
        "project_id": "p1",
        "service_name": "s1",
        "error_fingerprint": "abc",
        "http_status": 500,
        "route_template": "/test",
        "severity": "HIGH",
        "count": 1,
        "body": "SELECT * FROM users WHERE password='xyz'",  # FORBIDDEN!
    }

    with pytest.raises(ValueError, match="CRITICAL SECURITY VIOLATION"):
        validate_egress_payload(forbidden_payload)


def test_preview_llm_prompt_scrubs_secrets():
    code_with_secret = "const apikey = 'skl_live_998877665544332211'; fetch('https://api.internal/pay');"
    preview = preview_llm_prompt(
        incident_summary="Token expired error for ceo@company.io",
        route_path="/users/4821",
        proposed_code_snippet=code_with_secret,
    )

    # All secrets and PII must be scrubbed from LLM prompts!
    assert "skl_live_998877665544332211" not in preview
    assert "[REDACTED_SKELION_KEY]" in preview
    assert "ceo@company.io" not in preview
    assert "[REDACTED_EMAIL]" in preview
    assert "/users/:id" in preview
