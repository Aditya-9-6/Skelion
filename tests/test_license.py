# tests/test_license.py — Offline Ed25519 License Verification Acceptance Tests

import json
from datetime import datetime, timedelta, timezone
import pytest

from license.issuer import issue_license
from license.verifier import verify_license_offline


def test_offline_license_issuance_and_verification():
    # 1. Server issues license
    signed_license = issue_license(
        org_id="org_acme_labs",
        customer_name="Acme Corporation",
        customer_email="founder@acme.io",
        plan_id="local_team",
        duration_days=30,
        grace_days=7,
    )

    assert signed_license["license_format"] == "skelion-ed25519-v1"
    assert "signature" in signed_license
    assert signed_license["payload"]["plan"] == "local_team"

    # 2. Client verifies license 100% offline
    res = verify_license_offline(signed_license)
    assert res["status"] == "valid"
    assert res["valid"] is True
    assert res["plan"] == "local_team"
    assert "fix_generation" in res["features"]
    assert "mcp" in res["features"]


def test_tampered_license_signature_rejection():
    signed_license = issue_license(
        org_id="org_hacker",
        customer_name="Hacker Org",
        customer_email="hacker@evil.io",
        plan_id="local_solo",
        duration_days=30,
    )

    # Maliciously escalate privileges in payload
    signed_license["payload"]["plan"] = "local_enterprise"

    # Verifier MUST detect signature failure and degrade to local_community!
    res = verify_license_offline(signed_license)
    assert res["status"] == "degraded"
    assert res["valid"] is False
    assert res["plan"] == "local_community"
    assert "Cryptographic signature verification failed" in res["reason"]


def test_expired_license_grace_period():
    # Issue license that expired yesterday
    signed_license = issue_license(
        org_id="org_renew_soon",
        customer_name="Startup Inc",
        customer_email="cto@startup.io",
        plan_id="local_business",
        duration_days=-1,  # Expired 1 day ago
        grace_days=7,      # Has 7 days grace period
    )

    res = verify_license_offline(signed_license)
    assert res["status"] == "grace_period"
    assert res["valid"] is True
    assert res["plan"] == "local_business"
    assert "Grace period active" in res["message"]


def test_expired_license_past_grace_period_degradation():
    # Issue license that expired 15 days ago (past 7-day grace period)
    signed_license = issue_license(
        org_id="org_expired",
        customer_name="Old Customer",
        customer_email="billing@old.io",
        plan_id="local_team",
        duration_days=-15,
        grace_days=7,
    )

    res = verify_license_offline(signed_license)
    assert res["status"] == "degraded"
    assert res["valid"] is False
    assert res["plan"] == "local_community"
    # Never blocks traffic!
    assert "Proxy traffic is completely unaffected" in res["message"]
