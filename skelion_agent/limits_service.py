# skelion_agent/limits_service.py – Antigravity-Style Token Rate Limiter & Deduction Engine

"""Manages:
1. Universal Coding Tokens: High/low model weighting (e.g. Claude 3.5 Sonnet = 5x tokens, GPT-4o = 4x, Free = 1x).
2. Pacing Windows: 5-Hour Limit and Weekly Limit (mimicking Antigravity/Cursor limits).
3. Over-quota & Top-Up Priority: Purchased tokens used first, then monthly subscription tokens.
   User can toggle limit_enforcement_enabled OFF to consume purchased tokens at maximum speed.
4. Dedicated Skelion Autofix Pool: Standalone token pool for edge proxy incident repair.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
from sqlmodel import Session
from fastapi import HTTPException
from skelion_agent.models import Organization

# Model Multipliers for Universal Token Consumption
# Based on real-world cost ratios:
# Free / Flash tier: 1 token consumed per base credit unit
# GPT-4o Mini: 1x
# GPT-4o: 4x
# Claude 3.5 Sonnet: 5x
# Claude 3 Opus: 10x
MODEL_WEIGHTS: Dict[str, Dict[str, Any]] = {
    "free-tier-agent": {
        "name": "⚡ Skelion AI Lite (Active)",
        "available": True,
        "token_multiplier": 1,
        "description": "Multi-provider free key pool (Gemini 1.5 Flash + Groq + OpenRouter) with automated rotation.",
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "available": False,
        "token_multiplier": 1,
        "description": "Fast lightweight model (Requires connected OpenAI key).",
    },
    "gemini-1.5-flash": {
        "name": "Gemini 1.5 Flash",
        "available": False,
        "token_multiplier": 1,
        "description": "High speed reasoning (Requires connected Gemini key).",
    },
    "claude-3-5-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "available": False,
        "token_multiplier": 5,
        "description": "State-of-the-art coding (Requires connected Anthropic key).",
    },
    "gpt-4o": {
        "name": "GPT-4o Flagship",
        "available": False,
        "token_multiplier": 4,
        "description": "Flagship multi-modal model (Requires connected OpenAI key).",
    },
    "claude-3-opus": {
        "name": "Claude 3 Opus",
        "available": False,
        "token_multiplier": 10,
        "description": "Enterprise deep analysis (Requires connected Anthropic key).",
    },
}

# Antigravity-style Window Quotas per Tier (in effective universal tokens)
TIER_WINDOW_LIMITS = {
    "pilot": {
        "limit_5h": 50,       # 50 tokens per 5-hour window
        "limit_weekly": 100,  # 100 tokens per week
    },
    "starter": {
        "limit_5h": 500,      # 500 tokens per 5-hour window
        "limit_weekly": 1500, # 1,500 tokens per week
    },
    "pro": {
        "limit_5h": 1200,     # 1,200 tokens per 5-hour window
        "limit_weekly": 4000, # 4,000 tokens per week
    },
    "team": {
        "limit_5h": 4500,     # 4,500 tokens per 5-hour window
        "limit_weekly": 15000, # 15,000 tokens per week
    },
    "enterprise": {
        "limit_5h": 15000,
        "limit_weekly": 45000,
    },
    # Hosted Plans (v3 SaaS Proposal)
    "hosted_community": {
        "limit_5h": 50,
        "limit_weekly": 100,
    },
    "hosted_lite": {
        "limit_5h": 500,
        "limit_weekly": 1500,
    },
    "hosted_developer": {
        "limit_5h": 800,
        "limit_weekly": 2500,
    },
    "hosted_team": {
        "limit_5h": 4500,
        "limit_weekly": 15000,
    },
    "hosted_business": {
        "limit_5h": 12500,
        "limit_weekly": 40000,
    },
    "hosted_enterprise": {
        "limit_5h": 50000,
        "limit_weekly": 150000,
    },
    # Local BYO-LLM Plans
    "local_community": {
        "limit_5h": 100,
        "limit_weekly": 500,
    },
    "local_solo": {
        "limit_5h": 1000,
        "limit_weekly": 5000,
    },
    "local_team": {
        "limit_5h": 5000,
        "limit_weekly": 20000,
    },
    "local_business": {
        "limit_5h": 15000,
        "limit_weekly": 50000,
    },
    "local_enterprise": {
        "limit_5h": 50000,
        "limit_weekly": 150000,
    },
}


def check_and_reset_windows(org: Organization) -> bool:
    """Check 5h and weekly timestamp windows and reset used counters if window expired."""
    now = datetime.now(timezone.utc)
    changed = False

    # 5-hour window check
    w5_reset = org.window_5h_reset_at
    if w5_reset.tzinfo is None:
        w5_reset = w5_reset.replace(tzinfo=timezone.utc)
    if now >= w5_reset:
        org.window_5h_tokens_used = 0
        org.window_5h_reset_at = now + timedelta(hours=5)
        changed = True

    # Weekly window check
    ww_reset = org.window_weekly_reset_at
    if ww_reset.tzinfo is None:
        ww_reset = ww_reset.replace(tzinfo=timezone.utc)
    if now >= ww_reset:
        org.window_weekly_tokens_used = 0
        org.window_weekly_reset_at = now + timedelta(days=7)
        changed = True

    return changed


def get_token_status(org: Organization) -> Dict[str, Any]:
    """Calculate and return full breakdown of quotas, windows, and autofix tokens."""
    check_and_reset_windows(org)
    plan_limits = TIER_WINDOW_LIMITS.get(org.plan, TIER_WINDOW_LIMITS["pilot"])

    # Coding Tokens
    purchased_remaining = max(0, org.purchased_tokens - org.purchased_tokens_used)
    monthly_remaining = max(0, org.credits_total - org.credits_used)
    total_coding_tokens_remaining = purchased_remaining + monthly_remaining

    # Window Pacing
    w5_used = org.window_5h_tokens_used
    w5_limit = plan_limits["limit_5h"]
    w5_remaining = max(0, w5_limit - w5_used)

    weekly_used = org.window_weekly_tokens_used
    weekly_limit = plan_limits["limit_weekly"]
    weekly_remaining = max(0, weekly_limit - weekly_used)

    # Calculate reset seconds remaining
    now = datetime.now(timezone.utc)
    w5_reset = org.window_5h_reset_at.replace(tzinfo=timezone.utc) if org.window_5h_reset_at.tzinfo is None else org.window_5h_reset_at
    ww_reset = org.window_weekly_reset_at.replace(tzinfo=timezone.utc) if org.window_weekly_reset_at.tzinfo is None else org.window_weekly_reset_at

    sec_5h = max(0, int((w5_reset - now).total_seconds()))
    sec_weekly = max(0, int((ww_reset - now).total_seconds()))

    # Autofix Dedicated Tokens
    autofix_remaining = max(0, org.autofix_tokens_total - org.autofix_tokens_used)

    return {
        "plan": org.plan,
        "coding_tokens": {
            "total_remaining": total_coding_tokens_remaining,
            "purchased_remaining": purchased_remaining,
            "monthly_remaining": monthly_remaining,
            "limit_enforcement_enabled": org.limit_enforcement_enabled,
        },
        "windows": {
            "five_hour": {
                "used": w5_used,
                "limit": w5_limit,
                "remaining": w5_remaining,
                "resets_in_seconds": sec_5h,
                "resets_in_human": f"{sec_5h // 3600}h {(sec_5h % 3600) // 60}m",
                "percentage_used": round((w5_used / w5_limit) * 100, 1),
            },
            "weekly": {
                "used": weekly_used,
                "limit": weekly_limit,
                "remaining": weekly_remaining,
                "resets_in_seconds": sec_weekly,
                "resets_in_human": f"{sec_weekly // 86400}d {(sec_weekly % 86400) // 3600}h",
                "percentage_used": round((weekly_used / weekly_limit) * 100, 1),
            },
        },
        "autofix_tokens": {
            "total": org.autofix_tokens_total,
            "used": org.autofix_tokens_used,
            "remaining": autofix_remaining,
            "per_fix_cost_estimated": 250,  # ~250 tokens per incident diff
        },
    }


def deduct_coding_tokens(org: Organization, model_id: str, db: Session) -> Tuple[int, str]:
    """Verify window limits, model availability, and deduct universal coding tokens."""
    alias_map = {
        "skelion-ai-lite": "free-tier-agent",
        "skelion-lite": "free-tier-agent",
        "default": "free-tier-agent",
    }
    model_id = alias_map.get(model_id, model_id)
    model_info = MODEL_WEIGHTS.get(model_id)
    if not model_info:
        raise HTTPException(status_code=400, detail=f"Unknown model '{model_id}'")

    if not model_info["available"]:
        raise HTTPException(
            status_code=400,
            detail=f"Currently {model_info['name']} is not available. Please select the 'Free Tier Agent' which is connected to active API keys.",
        )

    check_and_reset_windows(org)
    cost = model_info["token_multiplier"]

    # 1. Check window limits if enforcement is enabled
    # User can turn off window limits if they have purchased tokens!
    plan_limits = TIER_WINDOW_LIMITS.get(org.plan, TIER_WINDOW_LIMITS["pilot"])
    purchased_remaining = max(0, org.purchased_tokens - org.purchased_tokens_used)

    if org.limit_enforcement_enabled or purchased_remaining == 0:
        if org.window_5h_tokens_used + cost > plan_limits["limit_5h"]:
            now = datetime.now(timezone.utc)
            reset_ts = org.window_5h_reset_at.replace(tzinfo=timezone.utc) if org.window_5h_reset_at.tzinfo is None else org.window_5h_reset_at
            sec = max(0, int((reset_ts - now).total_seconds()))
            raise HTTPException(
                status_code=429,
                detail=f"5-Hour Limit reached ({org.window_5h_tokens_used}/{plan_limits['limit_5h']} tokens used). Resets in {sec // 3600}h {(sec % 3600) // 60}m. Top up purchased tokens or wait for window reset.",
            )

        if org.window_weekly_tokens_used + cost > plan_limits["limit_weekly"]:
            raise HTTPException(
                status_code=429,
                detail=f"Weekly Limit reached ({org.window_weekly_tokens_used}/{plan_limits['limit_weekly']} tokens used). Resets weekly.",
            )

    # 2. Check token balance (purchased tokens consumed first, then monthly subscription quota)
    monthly_remaining = max(0, org.credits_total - org.credits_used)
    if purchased_remaining >= cost:
        org.purchased_tokens_used += cost
        bucket = "purchased"
    elif monthly_remaining >= cost:
        org.credits_used += cost
        bucket = "monthly"
    else:
        raise HTTPException(
            status_code=429,
            detail="All coding tokens exhausted! Purchase additional top-up tokens or upgrade plan.",
        )

    # Record window usage
    org.window_5h_tokens_used += cost
    org.window_weekly_tokens_used += cost

    db.add(org)
    db.commit()
    db.refresh(org)
    return cost, bucket


def deduct_autofix_tokens(org: Organization, estimated_tokens: int, db: Session) -> int:
    """Deduct tokens from the dedicated Skelion Autofix token pool."""
    remaining = max(0, org.autofix_tokens_total - org.autofix_tokens_used)
    if remaining < estimated_tokens:
        raise HTTPException(
            status_code=429,
            detail=f"Insufficient Skelion Autofix tokens! Required: {estimated_tokens}, Remaining: {remaining}. Purchase additional Autofix tokens to continue self-healing.",
        )

    org.autofix_tokens_used += estimated_tokens
    db.add(org)
    db.commit()
    db.refresh(org)
    return org.autofix_tokens_used
