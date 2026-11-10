# skelion_agent/pr_review_models.py
"""
SQLModel database models for the Skelion PR Review Platform.
Implements:
- installations
- repositories
- pull_requests
- review_runs
- findings
- evidence
- fixes
- feedback
- suppressions
- llm_cache
- commands
- webhook_deliveries
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid
from sqlmodel import SQLModel, Field, Column, JSON, UniqueConstraint


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Installation(SQLModel, table=True):
    __tablename__ = "installations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    github_installation_id: int = Field(index=True, unique=True)
    account_login: str = Field(index=True)
    status: str = Field(default="active")
    kill_switch: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class Repository(SQLModel, table=True):
    __tablename__ = "repositories"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    installation_id: Optional[str] = Field(default=None, foreign_key="installations.id", index=True)
    github_repo_id: int = Field(index=True, unique=True)
    full_name: str = Field(index=True)
    default_branch: str = Field(default="main")
    protected_branches: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    config_sha: Optional[str] = Field(default=None)
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    plan_tier: str = Field(default="free")
    fix_mode: str = Field(default="suggest")
    created_at: datetime = Field(default_factory=utc_now)


class PullRequest(SQLModel, table=True):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repository_id", "number", name="uq_pull_requests_repo_number"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    repository_id: str = Field(foreign_key="repositories.id", index=True)
    number: int = Field(index=True)
    title_hash: Optional[str] = Field(default=None)
    base_sha: str
    head_sha: str = Field(index=True)
    state: str = Field(default="open")
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewRun(SQLModel, table=True):
    __tablename__ = "review_runs"
    __table_args__ = (
        UniqueConstraint("pull_request_id", "head_sha", "config_sha", name="uq_review_runs_pr_head_config"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    pull_request_id: str = Field(foreign_key="pull_requests.id", index=True)
    head_sha: str = Field(index=True)
    base_sha: str
    config_sha: Optional[str] = Field(default=None)
    status: str = Field(default="queued")
    lanes: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    credits_estimated_milli: int = Field(default=0)
    credits_used_milli: int = Field(default=0)
    mode: str = Field(default="full")
    is_fork: bool = Field(default=False)
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)
    superseded_by: Optional[str] = Field(default=None, foreign_key="review_runs.id")


class Finding(SQLModel, table=True):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("pull_request_id", "fingerprint", name="uq_findings_pr_fingerprint"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    review_run_id: str = Field(foreign_key="review_runs.id", index=True)
    pull_request_id: Optional[str] = Field(default=None, foreign_key="pull_requests.id", index=True)
    fingerprint: str = Field(index=True)
    lane: str
    rule_id: str
    category: str = Field(default="security")
    file_path: str
    start_line: int
    end_line: int
    severity: str = Field(default="medium")
    confidence: str = Field(default="medium")
    impact_factor: float = Field(default=1.0)
    status: str = Field(default="open")
    github_comment_node_id: Optional[str] = Field(default=None)
    first_seen_sha: Optional[str] = Field(default=None)
    last_seen_sha: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    owner: Optional[str] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)


class Evidence(SQLModel, table=True):
    __tablename__ = "evidence"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    finding_id: str = Field(foreign_key="findings.id", index=True)
    type: str
    ref: Optional[str] = Field(default=None)
    redacted_payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    sha256: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Fix(SQLModel, table=True):
    __tablename__ = "fixes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    finding_id: str = Field(foreign_key="findings.id", index=True)
    fix_type: str = Field(default="patch")
    diff_sha256: str = Field(index=True)
    status: str = Field(default="proposed")
    verdict_reason: Optional[str] = Field(default=None)
    branch: Optional[str] = Field(default=None)
    commit_sha: Optional[str] = Field(default=None)
    evidence_bundle: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    finding_id: str = Field(foreign_key="findings.id", index=True)
    actor_id: str = Field(index=True)
    kind: str
    reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class Suppression(SQLModel, table=True):
    __tablename__ = "suppressions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    repository_id: str = Field(foreign_key="repositories.id", index=True)
    rule_id: Optional[str] = Field(default=None, index=True)
    path_pattern: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    owner: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = Field(default=None)


class LLMCache(SQLModel, table=True):
    __tablename__ = "llm_cache"

    chunk_sha256: str = Field(primary_key=True)
    model: str = Field(index=True)
    rate_card_version: str = Field(default="v1")
    output: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class Command(SQLModel, table=True):
    __tablename__ = "commands"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    repository_id: str = Field(foreign_key="repositories.id", index=True)
    pull_request_id: Optional[str] = Field(default=None, foreign_key="pull_requests.id", index=True)
    actor_id: str = Field(index=True)
    command: str
    args: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="pending")
    error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class WebhookDelivery(SQLModel, table=True):
    __tablename__ = "webhook_deliveries"

    delivery_id: str = Field(primary_key=True)
    event: str = Field(index=True)
    received_at: datetime = Field(default_factory=utc_now)
    processed_at: Optional[datetime] = Field(default=None)
    error: Optional[str] = Field(default=None)


# Aliases for plural/table names
Installations = Installation
Repositories = Repository
PullRequests = PullRequest
ReviewRuns = ReviewRun
Findings = Finding
Fixes = Fix
FeedbackRecords = Feedback
Suppressions = Suppression
LLMCaches = LLMCache
Commands = Command
WebhookDeliveries = WebhookDelivery

__all__ = [
    "utc_now",
    "Installation",
    "Repository",
    "PullRequest",
    "ReviewRun",
    "Finding",
    "Evidence",
    "Fix",
    "Feedback",
    "Suppression",
    "LLMCache",
    "Command",
    "WebhookDelivery",
    "Installations",
    "Repositories",
    "PullRequests",
    "ReviewRuns",
    "Findings",
    "Fixes",
    "FeedbackRecords",
    "Suppressions",
    "LLMCaches",
    "Commands",
    "WebhookDeliveries",
]
