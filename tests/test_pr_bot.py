# tests/test_pr_bot.py — PR Diagnostic Card & Webhook Tests

import hmac
import hashlib
from skelion_agent.pr_comment_bot import (
    generate_pr_diagnostic_card,
    verify_github_signature,
)
from skelion_agent.models import Incident


def test_generate_pr_diagnostic_card():
    inc = Incident(
        id="inc_pr_test",
        org_id="org_default",
        route_path="/api/billing/charge",
        http_method="GET",
        captured_method="GET",
        status_code=500,
        error_summary="Internal server error on billing charge",
        fingerprint="fp_card_abc123",
    )
    diff = "--- a/billing.py\n+++ b/billing.py\n@@ -1 +1 @@\n-broken\n+fixed"
    card = generate_pr_diagnostic_card(
        inc, "https://github.com/org/repo/pull/42", proposed_diff=diff
    )

    assert "Skelion Production Fix & Verification Report" in card
    assert "/api/billing/charge" in card
    assert "Replay Sandbox Verification Results" in card
    assert "View Proposed Patch Diff" in card
    assert "skelion-fix" in card


def test_github_signature_verification():
    secret = "my_webhook_secret_123"
    payload = b'{"action": "opened", "pull_request": {"number": 10}}'
    correct_sig = (
        "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    )

    assert verify_github_signature(payload, correct_sig, secret) is True
    assert verify_github_signature(payload, "sha256=invalid", secret) is False
    assert verify_github_signature(payload, None, secret) is False
