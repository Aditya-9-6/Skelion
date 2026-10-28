# skelion_agent/plan_config.py
"""Plan configuration for Skelion SaaS — Final Proposal v3.

Source of Truth: C:\\Users\\adity\\Downloads\\SKELION_PRICING_AND_BILLING_FINAL.md
Includes:
- Two decoupled product streams: Hosted (credits) vs Local (flat on-prem/BYO-LLM)
- The Cost x 3 debit rule (1 credit = 1 INR value, debited at 3x actual cost)
- Tiered credit packs (small, medium, large)
- Founding coupons, paid setup services, and legacy aliases
"""

import math
from typing import Dict, Any, Optional

# Global pricing parameters
VERSION = 3
FX_INR_PER_USD = 86.0            # Used for cost-basis estimates
CREDIT_INR_VALUE = 1.0           # 1 credit = 1 INR of usage value
MARKUP_ON_COST = 3.0             # Debit = actual_cost * 3
OVERHEAD_ON_COST = 0.15          # Retries, network failures, container compute
FREE_TIER_BUDGET_INR_PER_MONTH = 5000

# Hosted Plans (we run LLM & infrastructure; plans include usage credits)
HOSTED_PLANS: Dict[str, Dict[str, Any]] = {
    "hosted_community": {
        "id": "hosted_community",
        "name": "Hosted Community",
        "price_inr": 0,
        "credits": 50,
        "models": ["economy"],
        "seats": 1,
        "projects": 1,
        "retention_days": 7,
    },
    "hosted_lite": {
        "id": "hosted_lite",
        "name": "Skelion AI Lite (Pilot 30% Off)",
        "price_inr": 559,               # 30% discount off standard ₹799
        "annual_price_inr": 5590,
        "credits": 500,
        "models": ["economy"],          # Exclusively uses free AI tier (Skelion AI Lite)
        "seats": 1,
        "projects": 2,
        "retention_days": 14,
        "is_pilot_special": True,
    },
    "hosted_developer": {
        "id": "hosted_developer",
        "name": "Hosted Developer",
        "price_inr": 799,
        "annual_price_inr": 7990,
        "credits": 800,
        "models": ["economy", "standard"],
        "seats": 1,
        "projects": 3,
        "retention_days": 30,
    },
    "hosted_team": {
        "id": "hosted_team",
        "name": "Hosted Team",
        "price_inr": 3999,
        "annual_price_inr": 39990,
        "credits": 4500,
        "models": ["economy", "standard"],
        "seats": 5,
        "projects": 10,
        "retention_days": 90,
        "extra_seat_inr": 499,
    },
    "hosted_business": {
        "id": "hosted_business",
        "name": "Hosted Business",
        "price_inr": 9999,
        "annual_price_inr": 99990,
        "credits": 12500,
        "models": ["economy", "standard", "premium"],
        "seats": 20,
        "projects": 50,
        "retention_days": 365,
        "extra_seat_inr": 399,
    },
    "hosted_enterprise": {
        "id": "hosted_enterprise",
        "name": "Hosted Enterprise",
        "contact_sales": True,
        "from_inr": 40000,
        "annual_only": True,
        "credits": 50000,
        "seats": 999,
        "projects": 999,
    },
}

# Local Plans (customer's own LLM key or local model; zero marginal LLM cost; no credits)
LOCAL_PLANS: Dict[str, Dict[str, Any]] = {
    "local_community": {
        "id": "local_community",
        "name": "Local Community",
        "price_inr": 0,
        "projects": 1,
        "seats": 1,
    },
    "local_solo": {
        "id": "local_solo",
        "name": "Local Solo",
        "price_inr": 999,
        "price_usd": 19,
        "annual_price_inr": 9990,
        "projects": 1,
        "seats": 1,
    },
    "local_team": {
        "id": "local_team",
        "name": "Local Team",
        "price_inr": 4999,
        "price_usd": 79,
        "annual_price_inr": 49990,
        "projects": 5,
        "seats": 999,  # Unlimited seats
    },
    "local_business": {
        "id": "local_business",
        "name": "Local Business",
        "price_inr": 14999,
        "price_usd": 199,
        "annual_price_inr": 149990,
        "projects": 20,
        "seats": 999,  # Unlimited seats
    },
    "local_enterprise": {
        "id": "local_enterprise",
        "name": "Local Enterprise",
        "contact_sales": True,
        "from_inr": 40000,
        "annual_only": True,
        "projects": 999,
        "seats": 999,
    },
}

# Credit Packs (Hosted only; top-ups never beat upgrading)
CREDIT_PACKS: Dict[str, Dict[str, Any]] = {
    "small": {
        "id": "small",
        "name": "Small Credit Pack",
        "price_inr": 599,
        "credits": 500,
        "inr_per_credit": 1.20,
        "valid_months": 12,
    },
    "medium": {
        "id": "medium",
        "name": "Medium Credit Pack",
        "price_inr": 1699,
        "credits": 1500,
        "inr_per_credit": 1.13,
        "valid_months": 12,
    },
    "large": {
        "id": "large",
        "name": "Large Credit Pack",
        "price_inr": 5499,
        "credits": 5000,
        "inr_per_credit": 1.10,
        "valid_months": 12,
    },
}

# Paid setup & onboarding services
SERVICES: Dict[str, int] = {
    "setup_standard_inr": 7500,
    "setup_multi_service_inr": 15000,
}

# Coupons & Special Offers
COUPONS: Dict[str, Dict[str, Any]] = {
    "FOUNDING50": {
        "code": "FOUNDING50",
        "discount_percent": 30,  # 30% off for 12 months per spec
        "duration_months": 12,
        "max_redemptions": 50,
        "active": True,
        "description": "Founding Developer discount: 30% off any tier for 12 months.",
    },
    "EARLYBIRD": {
        "code": "EARLYBIRD",
        "discount_percent": 20,
        "duration_months": 3,
        "max_redemptions": 100,
        "active": True,
        "description": "Early adopter 20% discount for first quarter.",
    },
    "STUDENT_OSS": {
        "code": "STUDENT_OSS",
        "discount_percent": 50,
        "duration_months": 12,
        "max_redemptions": 500,
        "active": True,
        "description": "Student & Open Source Maintainer 50% discount.",
    },
}

# Consolidated Plan Definitions (with legacy compatibility aliases)
PLAN_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Hosted v3 canonical IDs
    "hosted_community": {"price": 0, "quota": 50},
    "hosted_lite": {"price": 559, "quota": 500},
    "hosted_developer": {"price": 799, "quota": 800},
    "hosted_team": {"price": 3999, "quota": 4500},
    "hosted_business": {"price": 9999, "quota": 12500},
    "hosted_enterprise": {"price": 40000, "quota": 50000},

    # Local v3 canonical IDs
    "local_community": {"price": 0, "quota": 0},
    "local_solo": {"price": 999, "quota": 0},
    "local_team": {"price": 4999, "quota": 0},
    "local_business": {"price": 14999, "quota": 0},
    "local_enterprise": {"price": 40000, "quota": 0},

    # Legacy aliases mapped to v3 equivalents
    "pilot": {"price": 0, "quota": 50},
    "starter": {"price": 799, "quota": 800},
    "pro": {"price": 3999, "quota": 4500},
    "team": {"price": 3999, "quota": 4500},
    "enterprise": {"price": 9999, "quota": 12500},
}


# Model token pricing tiers (USD per 1M tokens: input, output)
MODEL_TIER_RATES = {
    "economy": {"input": 0.30, "output": 2.00},   # e.g. GPT-4o Mini, Gemini 1.5 Flash
    "standard": {"input": 1.50, "output": 9.00},  # e.g. Claude 3.5 Sonnet standard, GPT-4o standard
    "premium": {"input": 3.00, "output": 15.00},  # e.g. Claude 3.5 Opus, specialized fine-tunes
}


def calculate_action_debit(
    tokens_in: int,
    tokens_out: int,
    model_tier: str = "standard",
    sandbox_minutes: float = 0.0,
) -> int:
    """Calculate debited credits using the strict Cost x 3 Rule (§4.1).
    
    cost = token_cost + sandbox_compute + 15% overhead
    debit = ceil(cost_inr * 3)
    Guarantees ~60-67% gross margin across all runs.
    """
    tier_rates = MODEL_TIER_RATES.get(model_tier, MODEL_TIER_RATES["standard"])
    token_cost_usd = (tokens_in / 1_000_000.0) * tier_rates["input"] + (tokens_out / 1_000_000.0) * tier_rates["output"]
    sandbox_cost_usd = (sandbox_minutes / 60.0) * 0.05  # ~$0.05/hr micro-container share
    
    subtotal_usd = token_cost_usd + sandbox_cost_usd
    subtotal_inr = subtotal_usd * FX_INR_PER_USD
    actual_cost_inr = subtotal_inr * (1.0 + OVERHEAD_ON_COST)

    debit_credits = math.ceil(actual_cost_inr * MARKUP_ON_COST)
    return max(1, debit_credits)


def get_discounted_price(plan_id: str, coupon_code: Optional[str] = None) -> int:
    """Calculate the final INR price after applying valid coupon discount."""
    base_price = PLAN_DEFINITIONS.get(plan_id, {}).get("price", 0)
    if not coupon_code or coupon_code.upper() not in COUPONS:
        return base_price

    coupon = COUPONS[coupon_code.upper()]
    if not coupon.get("active", False):
        return base_price

    discount = (base_price * coupon["discount_percent"]) // 100
    return max(0, base_price - discount)
