# core/entitlements.py — Centralized Feature Entitlements & Plan Limits (Apache-2.0 Open Core)

from typing import Dict, Any

# ---------------------------------------------------------------------------
# Feature & Limits Definitions Across Hosted and Local SKUs
# ---------------------------------------------------------------------------

PLAN_ENTITLEMENTS: Dict[str, Dict[str, Any]] = {
    # Hosted SKUs
    "hosted_community": {
        "name": "Community (Free)",
        "sku": "hosted",
        "limits": {
            "projects": 1,
            "seats": 1,
            "monthly_credits": 50,
            "requests_quota": 1000,
            "retention_days": 7,
        },
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "replay_preview",
        ],
    },
    "hosted_developer": {
        "name": "Developer Tier",
        "sku": "hosted",
        "limits": {
            "projects": 3,
            "seats": 1,
            "monthly_credits": 800,
            "requests_quota": 10000,
            "retention_days": 30,
        },
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "replay_preview",
            "fix_generation",
            "key_pooling",
            "email_alerts",
        ],
    },
    "hosted_team": {
        "name": "Team Tier",
        "sku": "hosted",
        "limits": {
            "projects": 10,
            "seats": 5,
            "monthly_credits": 4500,
            "requests_quota": 50000,
            "retention_days": 90,
        },
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "replay_preview",
            "fix_generation",
            "replay_verify",
            "key_pooling",
            "email_alerts",
            "pr_bot",
            "slack",
            "mcp",
            "team_dashboard",
        ],
    },
    "hosted_business": {
        "name": "Business Tier",
        "sku": "hosted",
        "limits": {
            "projects": 50,
            "seats": 20,
            "monthly_credits": 12500,
            "requests_quota": 250000,
            "retention_days": 365,
        },
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "replay_preview",
            "fix_generation",
            "replay_verify",
            "key_pooling",
            "email_alerts",
            "pr_bot",
            "slack",
            "mcp",
            "team_dashboard",
            "sso_mfa",
            "audit_log",
            "auto_merge_guardrails",
        ],
    },
    # Local SKUs (Customer's LLM key or Local Model, No credits, Offline License)
    "local_community": {
        "name": "Local Community (Free)",
        "sku": "local",
        "limits": {"projects": 1, "seats": 1, "retention_days": 7},
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "audit_cli",
        ],
    },
    "local_solo": {
        "name": "Local Solo",
        "sku": "local",
        "limits": {"projects": 1, "seats": 1, "retention_days": 30},
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "audit_cli",
            "fix_generation",
            "replay_verify",
            "byo_llm",
        ],
    },
    "local_team": {
        "name": "Local Team",
        "sku": "local",
        "limits": {"projects": 5, "seats": 999, "retention_days": 90},
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "audit_cli",
            "fix_generation",
            "replay_verify",
            "byo_llm",
            "pr_bot",
            "slack",
            "mcp",
            "team_dashboard",
        ],
    },
    "local_business": {
        "name": "Local Business",
        "sku": "local",
        "limits": {"projects": 20, "seats": 999, "retention_days": 365},
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "audit_cli",
            "fix_generation",
            "replay_verify",
            "byo_llm",
            "pr_bot",
            "slack",
            "mcp",
            "team_dashboard",
            "sso_mfa",
            "audit_log",
            "auto_merge_guardrails",
        ],
    },
    "local_enterprise": {
        "name": "Local Enterprise",
        "sku": "local",
        "limits": {"projects": 999, "seats": 999, "retention_days": 730},
        "features": [
            "proxy_capture",
            "redaction",
            "incident_fingerprinting",
            "audit_cli",
            "fix_generation",
            "replay_verify",
            "byo_llm",
            "pr_bot",
            "slack",
            "mcp",
            "team_dashboard",
            "sso_mfa",
            "audit_log",
            "auto_merge_guardrails",
            "custom_contracts",
            "priority_support",
        ],
    },
}

# Aliases for backward compatibility with v1 plan identifiers
PLAN_ALIASES: Dict[str, str] = {
    "pilot": "hosted_community",
    "starter": "hosted_developer",
    "pro": "hosted_team",
    "team": "hosted_team",
    "enterprise": "hosted_business",
}


def normalize_plan_id(plan_id: str) -> str:
    """Map legacy or raw plan names to canonical entitlement plan IDs."""
    p = plan_id.lower().strip()
    return PLAN_ALIASES.get(p, p)


def can(plan_id: str, feature: str) -> bool:
    """Check if a plan is entitled to execute a given feature."""
    canonical = normalize_plan_id(plan_id)
    plan_data = PLAN_ENTITLEMENTS.get(canonical, PLAN_ENTITLEMENTS["hosted_community"])
    return feature in plan_data.get("features", [])


def limit(plan_id: str, limit_name: str, default: Any = 0) -> Any:
    """Get the numeric constraint or quota for a given limit name."""
    canonical = normalize_plan_id(plan_id)
    plan_data = PLAN_ENTITLEMENTS.get(canonical, PLAN_ENTITLEMENTS["hosted_community"])
    return plan_data.get("limits", {}).get(limit_name, default)


def explain_denial(plan_id: str, feature: str) -> str:
    """Return a developer-friendly explanation of why a feature is unavailable and how to unlock it."""
    canonical = normalize_plan_id(plan_id)
    current_name = PLAN_ENTITLEMENTS.get(canonical, {}).get("name", plan_id)

    # Find the lowest tier that unlocks this feature
    upgrade_tier = "Pro / Team Tier"
    for pid, data in PLAN_ENTITLEMENTS.items():
        if feature in data.get("features", []):
            upgrade_tier = data.get("name", pid)
            break

    feature_readable = feature.replace("_", " ").title()
    return (
        f"Feature '{feature_readable}' is not available on your current plan ({current_name}). "
        f"Upgrade to {upgrade_tier} to unlock this capability."
    )
