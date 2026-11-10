# skelion_agent/pr_review/models.py — Postgres/SQLModel Schema for PR Review Engine
"""
Data models matching Section 14 of the Skelion PR Review Engine Specification:
installations, repositories, pull_requests, review_runs, findings, evidence,
fixes, feedback, suppressions, llm_cache, commands, webhook_deliveries.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid
from sqlmodel import SQLModel, Field, Column, JSON


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Installation(SQLModel, table=True):
    __tablename__ = "pr_installations"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    github_installation_id: int = Field(unique=True, index=True)
    account_login: str = Field(index=True)
    status: str = Field(default="active")  # active, suspended, deleted
    kill_switch: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class Repository(SQLModel, table=True):
    __tablename__ = "pr_repositories"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    installation_id: Optional[str] = Field(default=None, foreign_key="pr_installations.id", index=True)
    github_repo_id: int = Field(unique=True, index=True)
    full_name: str = Field(index=True)
    default_branch: str = Field(default="main")
    protected_branches: List[str] = Field(default_factory=lambda: ["main", "master"], sa_column=Column(JSON))
    config_sha: Optional[str] = Field(default=None)
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    plan_tier: str = Field(default="Tier 2")  # Tier 1, Tier 2, Tier 3, Tier 4
    fix_mode: str = Field(default="suggest")  # suggest, command, fix_pr, auto
    is_fork: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class PullRequest(SQLModel, table=True):
    __tablename__ = "pr_pull_requests"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    repository_id: str = Field(foreign_key="pr_repositories.id", index=True)
    number: int = Field(index=True)
    title_hash: str = Field(default="")
    base_sha: str = Field(default="")
    head_sha: str = Field(default="")
    state: str = Field(default="open")  # open, closed, merged
    is_fork: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewRun(SQLModel, table=True):
    __tablename__ = "pr_review_runs"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    pull_request_id: str = Field(foreign_key="pr_pull_requests.id", index=True)
    head_sha: str = Field(index=True)
    base_sha: str = Field(default="")
    config_sha: str = Field(default="")
    status: str = Field(default="pending", index=True)  # pending, running, completed, superseded, failed
    lanes: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    credits_estimated_milli: int = Field(default=0)
    credits_used_milli: int = Field(default=0)
    is_byo: bool = Field(default=False)
    summary_comment_id: Optional[str] = Field(default=None)
    check_run_id: Optional[int] = Field(default=None)
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: Optional[datetime] = Field(default=None)
    superseded_by: Optional[str] = Field(default=None)


class Finding(SQLModel, table=True):
    __tablename__ = "pr_findings"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    pull_request_id: str = Field(foreign_key="pr_pull_requests.id", index=True)
    review_run_id: str = Field(foreign_key="pr_review_runs.id", index=True)
    fingerprint: str = Field(index=True)
    lane: str = Field(index=True)
    rule_id: str = Field(index=True)
    category: str = Field(default="quality")  # quality, security, performance, logic, breaking, etc.
    file_path: str = Field(index=True)
    start_line: int
    end_line: int
    severity: str = Field(default="medium")  # info, low, medium, high, critical
    confidence: float = Field(default=1.0)
    impact_factor: float = Field(default=0.0)
    claim: str = Field(default="")
    status: str = Field(default="new", index=True)  # new, posted, fixed, accepted_risk, suppressed, dismissed, stale
    github_comment_node_id: Optional[str] = Field(default=None)
    first_seen_sha: str = Field(default="")
    last_seen_sha: str = Field(default="")
    reason: Optional[str] = Field(default=None)
    owner: Optional[str] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)


class Evidence(SQLModel, table=True):
    __tablename__ = "pr_evidence"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    finding_id: str = Field(foreign_key="pr_findings.id", index=True)
    type: str = Field(default="tool_output")  # tool_output, test_result, runtime_data, code_quote
    ref: str = Field(default="")
    redacted_payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    sha256: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Fix(SQLModel, table=True):
    __tablename__ = "pr_fixes"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    finding_id: str = Field(foreign_key="pr_findings.id", index=True)
    fix_type: str = Field(default="F1")  # F1, F2, F3, F4, F5
    diff_unified: str = Field(default="")
    diff_sha256: str = Field(index=True)
    status: str = Field(
        default="proposed", index=True
    )  # proposed, verified, verified_with_gaps, unverified, applied, stale, reverted
    verdict_reason: Optional[str] = Field(default=None)
    branch: Optional[str] = Field(default=None)
    commit_sha: Optional[str] = Field(default=None)
    evidence_bundle: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class Feedback(SQLModel, table=True):
    __tablename__ = "pr_feedback"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    finding_id: str = Field(foreign_key="pr_findings.id", index=True)
    actor_id: str = Field(index=True)
    kind: str = Field(index=True)  # thumbs_up, thumbs_down, dismissed, resolved, ignored
    reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class Suppression(SQLModel, table=True):
    __tablename__ = "pr_suppressions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    repository_id: str = Field(foreign_key="pr_repositories.id", index=True)
    rule_id: str = Field(index=True)
    path_pattern: str = Field(default="*")
    reason: str = Field(default="")
    owner: str = Field(default="developer")
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = Field(default=None)


class LLMCache(SQLModel, table=True):
    __tablename__ = "pr_llm_cache"
    chunk_sha256: str = Field(primary_key=True)
    model: str = Field(index=True)
    rate_card_version: str = Field(default="v1")
    output: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class PRCommand(SQLModel, table=True):
    __tablename__ = "pr_commands"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    repository_id: str = Field(foreign_key="pr_repositories.id", index=True)
    pull_request_id: str = Field(foreign_key="pr_pull_requests.id", index=True)
    actor_id: str = Field(index=True)
    command: str = Field(index=True)
    args: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="pending")  # pending, executed, rejected
    response_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class WebhookDelivery(SQLModel, table=True):
    __tablename__ = "pr_webhook_deliveries"
    delivery_id: str = Field(primary_key=True)
    event: str = Field(index=True)
    received_at: datetime = Field(default_factory=utc_now)
    processed_at: Optional[datetime] = Field(default=None)
    error: Optional[str] = Field(default=None)
