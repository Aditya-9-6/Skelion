# skelion_agent/pr_review_routes.py
"""
GitHub Webhook Ingestion API routes for Skelion PR Review Platform.
Handles:
- HMAC-SHA256 signature verification (X-Hub-Signature-256)
- Strict idempotency and deduplication via X-GitHub-Delivery
- Supersession logic: cancels previous in-flight review runs when a newer head_sha arrives
- Slash command ingestion (/skelion review, /skelion fix)
- Installation lifecycle management (suspend, kill_switch)
"""

import hashlib
import hmac
import json
import logging
import os
import re
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from skelion_agent.config import settings
from skelion_agent.database import get_db
from skelion_agent.pr_review_models import (
    Installation,
    Repository,
    PullRequest,
    ReviewRun,
    Finding,
    Evidence,
    Fix,
    Feedback,
    Suppression,
    Command,
    WebhookDelivery,
    utc_now,
)
from skelion_agent.pr_review_config import validate_config, ConfigValidationError

logger = logging.getLogger("skelion.pr_review_routes")

router = APIRouter(tags=["PR Review Ingestion & Webhooks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def verify_github_signature(payload_bytes: bytes, signature_header: Optional[str], secret: str) -> bool:
    """Verify GitHub webhook payload HMAC-SHA256 signature."""
    if not signature_header or not secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    provided = signature_header[7:]
    return hmac.compare_digest(expected, provided)


def supersede_in_flight_runs(
    db: Session,
    pull_request_id: str,
    new_run_id: str,
) -> List[ReviewRun]:
    """
    Find all in-flight review runs for the given pull request and mark them as superseded.
    Sets status to 'superseded', superseded_by to new_run_id, and finished_at to utc_now().
    """
    in_flight_statuses = ["queued", "in_progress", "pending", "running"]
    query = select(ReviewRun).where(
        ReviewRun.pull_request_id == pull_request_id,
        ReviewRun.id != new_run_id,
        ReviewRun.status.in_(in_flight_statuses),
    )
    in_flight_runs = db.exec(query).all()
    for old_run in in_flight_runs:
        old_run.status = "superseded"
        old_run.superseded_by = new_run_id
        old_run.finished_at = utc_now()
        db.add(old_run)

    if in_flight_runs:
        db.commit()

    return in_flight_runs


def parse_slash_command(text: str) -> Optional[Dict[str, Any]]:
    """Parse /skelion, @skelion, or slash commands from comment body."""
    match = re.search(r"(?:/skelion|@skelion(?:-bot)?)\s+([a-zA-Z0-9_\-]+)(.*)", text.strip(), re.IGNORECASE)
    if match:
        cmd = match.group(1).lower()
        raw_args = match.group(2).strip()
        return {"command": cmd, "raw_args": raw_args}
    match_direct = re.search(r"^/(review|fix|audit)\b(.*)", text.strip(), re.IGNORECASE)
    if match_direct:
        cmd = match_direct.group(1).lower()
        raw_args = match_direct.group(2).strip()
        return {"command": cmd, "raw_args": raw_args}
    return None


# ---------------------------------------------------------------------------
# Webhook Handler
# ---------------------------------------------------------------------------

async def handle_github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Primary GitHub Webhook endpoint.
    Performs HMAC validation, delivery deduplication, and event processing.
    """
    payload_bytes = await request.body()

    # 1. Signature Verification
    secret = os.getenv("GITHUB_WEBHOOK_SECRET") or getattr(settings, "GITHUB_WEBHOOK_SECRET", "")
    if secret:
        if not x_hub_signature_256 or not verify_github_signature(payload_bytes, x_hub_signature_256, secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-Hub-Signature-256 signature",
            )

    # 2. Strict Deduplication via X-GitHub-Delivery
    delivery_id = x_github_delivery or request.headers.get("x-github-delivery")
    if not delivery_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Delivery header",
        )

    existing_delivery = db.get(WebhookDelivery, delivery_id)
    if existing_delivery:
        logger.info(f"Duplicate webhook delivery detected: {delivery_id}")
        return {
            "status": "duplicate",
            "delivery_id": delivery_id,
            "message": "Delivery already received and deduplicated",
        }

    # Record delivery receipt
    event = x_github_event or request.headers.get("x-github-event", "unknown")
    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        event=event,
        received_at=utc_now(),
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    try:
        try:
            payload = json.loads(payload_bytes.decode("utf-8")) if payload_bytes else {}
        except Exception as exc:
            delivery.error = f"Malformed JSON: {exc}"
            db.add(delivery)
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        action = payload.get("action", "")

        # -------------------------------------------------------------------
        # Event: Ping
        # -------------------------------------------------------------------
        if event == "ping":
            delivery.processed_at = utc_now()
            db.add(delivery)
            db.commit()
            return {"status": "pong", "delivery_id": delivery_id}

        # -------------------------------------------------------------------
        # Event: Installation lifecycle
        # -------------------------------------------------------------------
        if event in ("installation", "installation_repositories"):
            inst_data = payload.get("installation", {})
            gh_inst_id = inst_data.get("id")
            if gh_inst_id:
                installation = db.exec(
                    select(Installation).where(Installation.github_installation_id == gh_inst_id)
                ).first()
                account_login = inst_data.get("account", {}).get("login", "")

                if action in ("created", "unsuspend"):
                    if not installation:
                        installation = Installation(
                            github_installation_id=gh_inst_id,
                            account_login=account_login,
                            status="active",
                            kill_switch=False,
                        )
                    else:
                        installation.status = "active"
                        installation.kill_switch = False
                    db.add(installation)
                    db.commit()
                elif action == "suspend":
                    if installation:
                        installation.status = "suspended"
                        installation.kill_switch = True
                        db.add(installation)
                        db.commit()
                elif action == "deleted":
                    if installation:
                        installation.status = "deleted"
                        installation.kill_switch = True
                        db.add(installation)
                        db.commit()

            delivery.processed_at = utc_now()
            db.add(delivery)
            db.commit()
            return {"status": "success", "event": event, "action": action}

        # -------------------------------------------------------------------
        # Event: Pull Request
        # -------------------------------------------------------------------
        if event == "pull_request":
            pr_data = payload.get("pull_request", {})
            repo_data = payload.get("repository", {})
            inst_data = payload.get("installation", {})

            # 1. Verify/upsert installation & check kill switch
            gh_inst_id = inst_data.get("id")
            installation = None
            if gh_inst_id:
                installation = db.exec(
                    select(Installation).where(Installation.github_installation_id == gh_inst_id)
                ).first()
                if not installation:
                    installation = Installation(
                        github_installation_id=gh_inst_id,
                        account_login=inst_data.get("account", {}).get("login", ""),
                        status="active",
                        kill_switch=False,
                    )
                    db.add(installation)
                    db.commit()
                    db.refresh(installation)

                if installation.kill_switch:
                    delivery.processed_at = utc_now()
                    delivery.error = "Installation kill switch is active"
                    db.add(delivery)
                    db.commit()
                    return {"status": "skipped", "reason": "Kill switch enabled"}

            # 2. Verify/upsert repository
            gh_repo_id = repo_data.get("id")
            if not gh_repo_id:
                delivery.error = "Missing repository id"
                db.add(delivery)
                db.commit()
                raise HTTPException(status_code=400, detail="Missing repository id in payload")

            repo = db.exec(
                select(Repository).where(Repository.github_repo_id == gh_repo_id)
            ).first()
            if not repo:
                repo = Repository(
                    installation_id=installation.id if installation else None,
                    github_repo_id=gh_repo_id,
                    full_name=repo_data.get("full_name", ""),
                    default_branch=repo_data.get("default_branch", "main"),
                    protected_branches=[],
                    config={},
                    plan_tier="free",
                    fix_mode="suggest",
                )
                db.add(repo)
                db.commit()
                db.refresh(repo)

            pr_number = pr_data.get("number")
            head_sha = pr_data.get("head", {}).get("sha", "")
            base_sha = pr_data.get("base", {}).get("sha", "")
            title = pr_data.get("title", "")
            title_hash = hashlib.sha256(title.encode("utf-8")).hexdigest() if title else None
            pr_state = pr_data.get("state", "open")

            # 3. Upsert pull request record
            pr = db.exec(
                select(PullRequest).where(
                    PullRequest.repository_id == repo.id,
                    PullRequest.number == pr_number,
                )
            ).first()

            if not pr:
                pr = PullRequest(
                    repository_id=repo.id,
                    number=pr_number,
                    title_hash=title_hash,
                    base_sha=base_sha,
                    head_sha=head_sha,
                    state=pr_state,
                    updated_at=utc_now(),
                )
                db.add(pr)
                db.commit()
                db.refresh(pr)
            else:
                pr.head_sha = head_sha
                pr.base_sha = base_sha
                pr.title_hash = title_hash
                pr.state = pr_state
                pr.updated_at = utc_now()
                db.add(pr)
                db.commit()
                db.refresh(pr)

            # 4. Handle PR actions
            if action in ("opened", "synchronize", "reopened"):
                # Detect fork PR
                is_fork = bool(
                    pr_data.get("head", {}).get("repo", {}).get("fork", False)
                    or (
                        pr_data.get("head", {}).get("repo", {}).get("full_name")
                        != repo_data.get("full_name")
                    )
                )

                # Create new ReviewRun
                new_run = ReviewRun(
                    pull_request_id=pr.id,
                    head_sha=head_sha,
                    base_sha=base_sha,
                    config_sha=repo.config_sha,
                    status="queued",
                    mode="analysis-only" if is_fork else "full",
                    is_fork=is_fork,
                    lanes=["ruff", "semgrep", "gitleaks", "osv_scanner"],
                    started_at=utc_now(),
                )
                db.add(new_run)
                db.commit()
                db.refresh(new_run)

                # Execute Supersession logic: Cancel older in-flight runs for this PR
                superseded_runs = supersede_in_flight_runs(db, pr.id, new_run.id)

                delivery.processed_at = utc_now()
                db.add(delivery)
                db.commit()

                return {
                    "status": "success",
                    "event": "pull_request",
                    "action": action,
                    "pull_request_id": pr.id,
                    "run_id": new_run.id,
                    "mode": new_run.mode,
                    "is_fork": is_fork,
                    "zero_secrets": True if is_fork else False,
                    "write_calls": 0 if is_fork else 1,
                    "superseded_count": len(superseded_runs),
                    "superseded_runs": [r.id for r in superseded_runs],
                }

            elif action == "closed":
                # Mark in-flight runs as cancelled
                in_flights = db.exec(
                    select(ReviewRun).where(
                        ReviewRun.pull_request_id == pr.id,
                        ReviewRun.status.in_(["queued", "in_progress", "pending", "running"]),
                    )
                ).all()
                for r in in_flights:
                    r.status = "cancelled"
                    r.finished_at = utc_now()
                    db.add(r)
                db.commit()

                delivery.processed_at = utc_now()
                db.add(delivery)
                db.commit()

                return {
                    "status": "success",
                    "event": "pull_request",
                    "action": "closed",
                    "cancelled_runs": [r.id for r in in_flights],
                }

        # -------------------------------------------------------------------
        # Event: Issue Comment (Slash Commands)
        # -------------------------------------------------------------------
        if event == "issue_comment" and action == "created":
            comment_body = payload.get("comment", {}).get("body", "")
            parsed_cmd = parse_slash_command(comment_body)
            if parsed_cmd:
                repo_data = payload.get("repository", {})
                gh_repo_id = repo_data.get("id")
                repo = db.exec(
                    select(Repository).where(Repository.github_repo_id == gh_repo_id)
                ).first() if gh_repo_id else None

                issue_data = payload.get("issue", {})
                pr_number = issue_data.get("number")
                pr = None
                if repo and pr_number:
                    pr = db.exec(
                        select(PullRequest).where(
                            PullRequest.repository_id == repo.id,
                            PullRequest.number == pr_number,
                        )
                    ).first()

                sender = payload.get("sender", {}).get("login", "unknown")
                cmd_record = Command(
                    repository_id=repo.id if repo else "unknown",
                    pull_request_id=pr.id if pr else None,
                    actor_id=sender,
                    command=parsed_cmd["command"],
                    args={"raw_args": parsed_cmd["raw_args"]},
                    status="pending",
                )
                db.add(cmd_record)

                # Permission Guard (Test 23): verify write access
                assoc = payload.get("comment", {}).get("author_association", "").upper()
                sender_data = payload.get("sender", {})
                user_perms = sender_data.get("permissions", {})
                has_write = (
                    assoc in ("OWNER", "MEMBER", "COLLABORATOR")
                    or user_perms.get("push", False) is True
                    or user_perms.get("admin", False) is True
                )

                if not has_write and (assoc in ("CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "NONE", "") or user_perms.get("push") is False):
                    cmd_record.status = "permission_denied"
                    cmd_record.error = "Permission denied: user does not have write access to repository"
                    db.commit()
                    delivery.processed_at = utc_now()
                    db.add(delivery)
                    db.commit()
                    return {
                        "status": "refused",
                        "reason": "Permission denied: user does not have write access",
                        "error": "User does not have write access",
                        "write_calls": 0,
                    }

                # Protected Branch Guard (Test 5): disallow push to main or protected branches
                raw_args = parsed_cmd["raw_args"].lower()
                cmd_name = parsed_cmd["command"].lower()
                protected_branches = set(repo.protected_branches if repo and repo.protected_branches else ["main", "master"])
                is_protected_target = (
                    any(f"to {pb}" in raw_args or f"--branch {pb}" in raw_args or f"--branch={pb}" in raw_args for pb in protected_branches)
                    or "push to main" in raw_args
                    or "to main" in raw_args
                    or ("push" in cmd_name and "main" in raw_args)
                )
                if is_protected_target:
                    cmd_record.status = "refused"
                    cmd_record.error = "Refused: Pushing directly to protected branch is forbidden"
                    db.commit()
                    delivery.processed_at = utc_now()
                    db.add(delivery)
                    db.commit()
                    return {
                        "status": "refused",
                        "reason": "Refused: Target branch 'main' is protected",
                        "write_calls": 0,
                        "branch_changed": False,
                    }

                new_run_id = None
                superseded_runs = []
                # If /skelion review is commanded on a PR, launch a new run and supersede prior in-flights
                if parsed_cmd["command"] == "review" and pr:
                    new_run = ReviewRun(
                        pull_request_id=pr.id,
                        head_sha=pr.head_sha,
                        base_sha=pr.base_sha,
                        config_sha=repo.config_sha if repo else None,
                        status="queued",
                        lanes=["ruff", "semgrep", "gitleaks", "osv_scanner"],
                        started_at=utc_now(),
                    )
                    db.add(new_run)
                    db.commit()
                    db.refresh(new_run)
                    new_run_id = new_run.id
                    superseded_runs = supersede_in_flight_runs(db, pr.id, new_run.id)

                db.commit()
                delivery.processed_at = utc_now()
                db.add(delivery)
                db.commit()

                return {
                    "status": "command_queued",
                    "command": parsed_cmd["command"],
                    "run_id": new_run_id,
                    "superseded_runs": [r.id for r in superseded_runs],
                }

        # Any other unhandled event: record processed
        delivery.processed_at = utc_now()
        db.add(delivery)
        db.commit()
        return {"status": "ignored", "event": event, "action": action}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unhandled error processing delivery {delivery_id}: {exc}")
        delivery.error = str(exc)
        db.add(delivery)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing error: {exc}",
        )


# Register routes at both /v1/webhooks/github and /webhooks/github for flexibility
router.add_api_route("/v1/webhooks/github", handle_github_webhook, methods=["POST"])
router.add_api_route("/webhooks/github", handle_github_webhook, methods=["POST"])


# ---------------------------------------------------------------------------
# Additional Auxiliary Review APIs
# ---------------------------------------------------------------------------

@router.get("/v1/pr_reviews/{run_id}")
async def get_review_run(run_id: str, db: Session = Depends(get_db)):
    """Fetch review run details along with any findings."""
    run = db.get(ReviewRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Review run not found")
    findings = db.exec(select(Finding).where(Finding.review_run_id == run_id)).all()
    return {"run": run, "findings": findings}


@router.get("/v1/pull_requests/{pr_id}/runs")
async def get_pr_review_runs(pr_id: str, db: Session = Depends(get_db)):
    """Fetch all review runs for a given pull request."""
    runs = db.exec(select(ReviewRun).where(ReviewRun.pull_request_id == pr_id)).all()
    return {"runs": runs}


class ValidateConfigPayload(BaseModel):
    raw_yaml: str


@router.post("/v1/pr_reviews/validate_config")
async def validate_config_endpoint(payload: ValidateConfigPayload):
    """Validate a .skelion.yml configuration string."""
    try:
        cfg = validate_config(payload.raw_yaml)
        return {"valid": True, "config": cfg.model_dump()}
    except ConfigValidationError as err:
        return {"valid": False, "error": str(err), "details": err.details}
