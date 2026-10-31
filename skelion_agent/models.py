# skelion_agent/models.py — Unified Multi-Tenant Schema (Devproxy + GossipMesh + Antigravity-Style Quotas)
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    token: str = Field(unique=True, index=True)  # Format: skl_live_<32_hex>
    plan: str = Field(default="pilot")  # pilot, pro, enterprise

    # Coding Agent Tokens (Monthly subscription allowance + Purchased top-up tokens)
    credits_total: int = Field(default=100)  # Monthly allowance
    credits_used: int = Field(default=0)
    purchased_tokens: int = Field(default=0)  # Top-up tokens (no expiry)
    purchased_tokens_used: int = Field(default=0)

    # Skelion Autofix Specific Tokens (Dedicated pool for DevProxy & self-healing)
    autofix_tokens_total: int = Field(default=50000)  # Free starting autofix tokens
    autofix_tokens_used: int = Field(default=0)

    # 5-Hour and Weekly Rate Limiting (Antigravity-Style pacing)
    limit_enforcement_enabled: bool = Field(
        default=True
    )  # User can disable for purchased tokens
    window_5h_tokens_used: int = Field(default=0)
    window_5h_reset_at: datetime = Field(default_factory=utc_now)
    window_weekly_tokens_used: int = Field(default=0)
    window_weekly_reset_at: datetime = Field(default_factory=utc_now)

    # Billing & Integration Keys
    razorpay_customer_id: Optional[str] = Field(default=None)
    stripe_customer_id: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    password_hash: Optional[str] = Field(default=None)
    stripe_subscription_status: str = Field(default="trialing")
    monthly_quota: int = Field(default=1000)
    quota_remaining: int = Field(default=1000)
    mfa_totp_secret: Optional[str] = Field(default=None)
    billing_email: Optional[str] = Field(default=None)
    github_id: Optional[int] = Field(default=None, index=True)
    github_username: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    github_installation_id: Optional[int] = Field(default=None)
    target_repo_full_name: Optional[str] = Field(default=None)
    auto_merge_non_breaking: bool = Field(default=False)

    # Phase 2 V2 Billing Fields
    is_personal: bool = Field(default=False)
    owner_user_id: Optional[str] = Field(default=None)
    plan_id: str = Field(default="hosted_community", index=True)
    plan_version: int = Field(default=1)
    billing_status: str = Field(
        default="active", index=True
    )  # active, grace, expired, canceled
    plan_period_start: Optional[datetime] = Field(default=None)
    plan_period_end: Optional[datetime] = Field(default=None)
    grace_until: Optional[datetime] = Field(default=None)
    cancel_at_period_end: bool = Field(default=False)
    pilot_until: Optional[datetime] = Field(default=None)
    gstin: Optional[str] = Field(default=None)
    billing_name: Optional[str] = Field(default=None)
    billing_address: Optional[str] = Field(default=None)
    billing_state: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class ProxyNode(SQLModel, table=True):
    __tablename__ = "proxy_nodes"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    node_name: str = Field(default="default-node")
    api_key_prefix: str = Field(default="skl_live_", index=True)
    api_key_hash: str = Field(unique=True, index=True)
    version: str = Field(default="0.1.0")
    last_heartbeat_at: Optional[datetime] = Field(default=None)
    routing_config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class Incident(SQLModel, table=True):
    __tablename__ = "incidents"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    fingerprint: str = Field(index=True)
    http_method: str
    route_path: str
    status_code: int
    error_summary: str
    captured_method: str = Field(default="GET")
    captured_headers: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    captured_body: str = Field(default="")
    latency_ms: float = Field(default=0.0)
    occurrence_count: int = Field(default=1)
    generated_diff: Optional[str] = Field(default=None)
    generated_test_file: Optional[str] = Field(default=None)
    sandbox_status: str = Field(default="pending")
    sandbox_review_summary: Optional[str] = Field(default=None)
    status: str = Field(default="analyzing")
    created_at: datetime = Field(default_factory=utc_now)
    last_seen_at: datetime = Field(default_factory=utc_now)


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    incident_id: str = Field(foreign_key="incidents.id", index=True)
    status: str = Field(default="running")
    pr_url: Optional[str] = Field(default=None)
    pr_number: Optional[int] = Field(default=None)
    cycles_executed: int = Field(default=1)
    llm_provider_used: Optional[str] = Field(default=None)
    execution_duration_sec: float = Field(default=0.0)
    error_log: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class PRReview(SQLModel, table=True):
    __tablename__ = "pr_reviews"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    repo_full_name: str = Field(index=True)
    pr_number: int = Field(index=True)
    head_sha: str
    security_verdict: str = Field(default="clean")
    review_card_markdown: Optional[str] = Field(default=None)
    credits_deducted: int = Field(default=1)
    status: str = Field(default="completed")
    created_at: datetime = Field(default_factory=utc_now)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    title: str = Field(default="New Chat")
    model: str = Field(default="free-tier-agent")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatMessageRecord(SQLModel, table=True):
    __tablename__ = "chat_messages"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id", index=True)
    role: str
    content: str
    tool_call_json: Optional[str] = Field(default=None)
    tokens_consumed: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)


class TransactionRecord(SQLModel, table=True):
    __tablename__ = "transactions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    order_id: str = Field(index=True)
    payment_id: Optional[str] = Field(default=None)
    category: str = Field(
        default="plan"
    )  # "plan", "topup_autofix", "topup_coding", "admin_credit"
    item_name: str = Field(default="")
    amount_inr: float = Field(default=0.0)
    tokens_granted: int = Field(default=0)
    status: str = Field(default="paid")  # "created", "paid", "refunded"
    created_at: datetime = Field(default_factory=utc_now)


# ---------------------------------------------------------------------------
# Phase 2 Billing v2 & License Models
# ---------------------------------------------------------------------------


class PaymentOrder(SQLModel, table=True):
    __tablename__ = "payment_orders"
    id: str = Field(
        default_factory=lambda: f"po_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    org_id: str = Field(foreign_key="organizations.id", index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    plan_id: Optional[str] = Field(default=None)
    plan_version: int = Field(default=1)
    kind: str = Field(
        default="plan", index=True
    )  # plan, renewal, pack, topup_autofix, manual
    amount_paise: int = Field(default=0)
    currency: str = Field(default="INR")
    gst_paise: int = Field(default=0)
    coupon_id: Optional[str] = Field(default=None)
    provider: str = Field(default="razorpay")  # razorpay, stripe, manual
    provider_order_id: Optional[str] = Field(default=None, unique=True, index=True)
    receipt: str = Field(default="")
    status: str = Field(
        default="created", index=True
    )  # created, paid, failed, expired, refunded
    expires_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    id: str = Field(
        default_factory=lambda: f"pay_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    payment_order_id: str = Field(foreign_key="payment_orders.id", index=True)
    provider_payment_id: str = Field(unique=True, index=True)
    amount_paise: int = Field(default=0)
    currency: str = Field(default="INR")
    method: str = Field(default="upi")
    status: str = Field(default="captured")
    captured_at: datetime = Field(default_factory=utc_now)
    raw_json: Optional[str] = Field(default=None)


class Refund(SQLModel, table=True):
    __tablename__ = "refunds"
    id: str = Field(
        default_factory=lambda: f"ref_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    payment_id: str = Field(foreign_key="payments.id", index=True)
    provider_refund_id: str = Field(unique=True, index=True)
    amount_paise: int = Field(default=0)
    status: str = Field(default="processed")
    reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class CreditLedger(SQLModel, table=True):
    __tablename__ = "credit_ledger"
    id: str = Field(
        default_factory=lambda: f"ledg_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    org_id: str = Field(foreign_key="organizations.id", index=True)
    bucket: str = Field(
        default="allowance", index=True
    )  # allowance, pack, grant, autofix
    delta: int = Field(
        default=0
    )  # positive for grants/topups, negative for usage/expirations
    reason: str = Field(
        default="plan_period"
    )  # plan_period, pack, pilot_grant, usage, refund, expiry, admin_adjust
    ref_type: Optional[str] = Field(default=None)  # payment, incident, run, chat
    ref_id: Optional[str] = Field(default=None)
    idempotency_key: str = Field(unique=True, index=True)
    cost_inr_est: float = Field(default=0.0)  # unit economics tracking
    expires_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class WebhookEvent(SQLModel, table=True):
    __tablename__ = "webhook_events"
    id: str = Field(
        default_factory=lambda: f"whe_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    provider: str = Field(default="razorpay", index=True)
    event_id: str = Field(index=True)
    event_type: str = Field(index=True)
    payload_json: str = Field(default="{}")
    status: str = Field(
        default="received", index=True
    )  # received, processed, failed, ignored
    error: Optional[str] = Field(default=None)
    received_at: datetime = Field(default_factory=utc_now)
    processed_at: Optional[datetime] = Field(default=None)


class Coupon(SQLModel, table=True):
    __tablename__ = "coupons"
    id: str = Field(
        default_factory=lambda: f"cpn_{uuid.uuid4().hex[:8]}", primary_key=True
    )
    code: str = Field(unique=True, index=True)
    kind: str = Field(default="percent")  # percent, fixed
    value: float = Field(default=30.0)  # 30% or ₹X
    plan_scope: str = Field(default="all")
    max_redemptions: int = Field(default=50)
    redemptions_count: int = Field(default=0)
    valid_until: Optional[datetime] = Field(default=None)
    price_lock_months: int = Field(default=12)
    active: bool = Field(default=True)


class CouponRedemption(SQLModel, table=True):
    __tablename__ = "coupon_redemptions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    coupon_id: str = Field(foreign_key="coupons.id", index=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    payment_order_id: str = Field(foreign_key="payment_orders.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    id: str = Field(
        default_factory=lambda: f"inv_{uuid.uuid4().hex[:10]}", primary_key=True
    )
    invoice_number: str = Field(unique=True, index=True)
    org_id: str = Field(foreign_key="organizations.id", index=True)
    payment_id: Optional[str] = Field(default=None)
    amount_paise: int = Field(default=0)
    gst_paise: int = Field(default=0)
    gstin_buyer: Optional[str] = Field(default=None)
    pdf_url: Optional[str] = Field(default=None)
    issued_at: datetime = Field(default_factory=utc_now)


class License(SQLModel, table=True):
    __tablename__ = "licenses"
    id: str = Field(
        default_factory=lambda: f"lic_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    org_id: str = Field(foreign_key="organizations.id", index=True)
    sku: str = Field(default="local", index=True)  # local, hybrid, cloud
    plan_id: str = Field(default="local_team", index=True)
    limits_json: str = Field(default="{}")
    features_json: str = Field(default="[]")
    signature: str = Field(default="")
    customer_name: Optional[str] = Field(default=None)
    customer_email: Optional[str] = Field(default=None)
    issued_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=utc_now)
    grace_days: int = Field(default=7)
    active: bool = Field(default=True)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    actor: str = Field(default="system", index=True)
    org_id: Optional[str] = Field(default=None, index=True)
    action: str = Field(index=True)
    meta_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)


# ---------------------------------------------------------------------------
# SaaS Multi-Tenant Team & Ingress Telemetry Models
# ---------------------------------------------------------------------------


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(
        default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    email: str = Field(unique=True, index=True)
    password_hash: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    is_verified: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)


class Membership(SQLModel, table=True):
    __tablename__ = "memberships"
    id: str = Field(
        default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    org_id: str = Field(foreign_key="organizations.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    role: str = Field(
        default="developer", index=True
    )  # owner, admin, developer, viewer
    created_at: datetime = Field(default_factory=utc_now)


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    id: str = Field(
        default_factory=lambda: f"key_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    org_id: str = Field(foreign_key="organizations.id", index=True)
    name: str = Field(default="Default Secret Key")
    key_prefix: str = Field(default="skl_live_", index=True)
    key_hash: str = Field(unique=True, index=True)
    scopes: str = Field(default="ingest,read")
    is_active: bool = Field(default=True, index=True)
    last_used_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class WebhookSubscription(SQLModel, table=True):
    __tablename__ = "webhook_subscriptions"
    id: str = Field(
        default_factory=lambda: f"whs_{uuid.uuid4().hex[:12]}", primary_key=True
    )
    org_id: str = Field(foreign_key="organizations.id", index=True)
    url: str
    secret: str = Field(default_factory=lambda: f"whsec_{uuid.uuid4().hex}")
    events_json: str = Field(default='["incident.created","fix.verified"]')
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
