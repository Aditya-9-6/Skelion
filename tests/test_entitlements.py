# tests/test_entitlements.py — Plan Entitlements & Limits Tests

from core.entitlements import can, limit, explain_denial


def test_entitlement_gating():
    # Community cannot generate fixes
    assert can("hosted_community", "fix_generation") is False
    assert can("local_community", "fix_generation") is False

    # Team and above can generate fixes and use MCP
    assert can("hosted_team", "fix_generation") is True
    assert can("hosted_team", "mcp") is True
    assert can("local_team", "fix_generation") is True
    assert can("local_team", "mcp") is True

    # Legacy alias mapping
    assert can("pro", "fix_generation") is True
    assert can("pilot", "fix_generation") is False


def test_limit_enforcement():
    assert limit("hosted_community", "projects") == 1
    assert limit("hosted_team", "projects") == 10
    assert limit("local_team", "projects") == 5


def test_denial_explanations():
    msg = explain_denial("hosted_community", "fix_generation")
    assert "not available on your current plan" in msg
    assert "Upgrade" in msg
