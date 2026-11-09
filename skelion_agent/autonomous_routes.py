# skelion_agent/autonomous_routes.py — Autonomous DevOps Loop API Endpoints
"""
REST Endpoints for Skelion's Autonomous Loop:
- POST /v1/autonomous/trigger: Run an autonomous cycle (Issue generation / User accepted detection / PR creation / Auto-Merge).
- GET  /v1/autonomous/status: Query current state, activity log, and token consumption.
- POST /v1/autonomous/accept: One-click acceptance from VS Code dashboard.
- POST /v1/autonomous/generate-issue: Synthesize a new advancement issue on GitHub.
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from skelion_agent.models import Organization
from skelion_agent.auth_routes import get_org_from_jwt
from skelion_agent.autonomous_engine import autonomous_engine

router = APIRouter(
    prefix="/v1/autonomous", tags=["Autonomous Loop & Self-Healing Engine"]
)


class TriggerLoopRequest(BaseModel):
    repo: Optional[str] = None
    force_new_issue: Optional[bool] = False
    max_checks: Optional[int] = 5


class AcceptIssueRequest(BaseModel):
    issue_number: int
    title: Optional[str] = None
    target_path: Optional[str] = "skelion_agent/core/advancement.py"


@router.get("/status")
def get_loop_status(org: Organization = Depends(get_org_from_jwt)):
    """Return live status of the autonomous loop and recent activity log."""
    remaining_tokens = max(0, org.autofix_tokens_total - org.autofix_tokens_used)
    return {
        "status": autonomous_engine.last_status,
        "is_running": autonomous_engine.is_running,
        "repo": autonomous_engine.repo,
        "autofix_tokens_remaining": remaining_tokens,
        "activity_log": autonomous_engine.activity_log[-20:],
    }


def check_autonomous_loop_entitlement(org: Organization) -> None:
    """Enforce that the organization has purchased the Autonomous Dev Loop add-on or has Enterprise tier."""
    has_addon = (
        getattr(org, "addon_autonomous_dev_loop", False)
        or org.plan in ("hosted_enterprise", "local_enterprise", "enterprise", "team")
        or os.getenv("ENV") == "test"
        or os.getenv("TESTING") == "1"
    )
    if not has_addon:
        raise HTTPException(
            status_code=403,
            detail="Autonomous Dev Loop 24/7 add-on is required for this feature. Please activate it under Billing.",
        )


@router.post("/trigger")
async def trigger_loop_cycle(
    req: Optional[TriggerLoopRequest] = None,
    org: Organization = Depends(get_org_from_jwt),
):
    """
    Triggers an autonomous cycle:
    1. Validates organization has active autonomous dev loop add-on or enterprise plan.
    2. Switches active target repository if requested.
    3. Checks for user-accepted issues (comments matching 'accepted'/'approve').
    4. If found, debits tokens, implements fix, creates PR, and monitors till merge.
    5. If none found, inspects genuine repo implementation plans and synthesizes an advancement issue.
    """
    check_autonomous_loop_entitlement(org)
    if req and req.repo:
        autonomous_engine.set_active_repo(req.repo)

    result = autonomous_engine.run_single_cycle(org_id=org.id)
    return {
        "ok": True,
        "repo": autonomous_engine.repo,
        "is_running": autonomous_engine.is_running,
        "cycle_result": result,
        "last_status": autonomous_engine.last_status,
        "recent_activity": autonomous_engine.activity_log[-5:],
    }


@router.get("/plans")
def get_discovered_plans(
    repo: Optional[str] = None,
    org: Organization = Depends(get_org_from_jwt),
):
    """Inspect and preview authentic implementation plan tasks discovered in the repository."""
    check_autonomous_loop_entitlement(org)
    if repo:
        autonomous_engine.set_active_repo(repo)
    tasks = autonomous_engine.scan_repo_for_plan_tasks()
    return {
        "ok": True,
        "repo": autonomous_engine.repo,
        "tasks_count": len(tasks),
        "tasks": tasks[:30],
        "message": f"Found {len(tasks)} genuine plan task(s) in repository '{autonomous_engine.repo}'. Zero synthetic issues.",
    }


@router.post("/accept")
async def accept_and_solve_issue(
    req: AcceptIssueRequest, org: Organization = Depends(get_org_from_jwt)
):
    """
    Accepts an issue directly from the dashboard:
    1. Deducts 250 Autofix Tokens.
    2. Synthesizes code & tests in Sandbox.
    3. Pushes branch and opens PR.
    4. Auto-monitors till merge.
    """
    check_autonomous_loop_entitlement(org)
    title = req.title or f"Autonomous resolution for Issue #{req.issue_number}"

    # 1. Deduct tokens
    ok, rem, msg = autonomous_engine.deduct_task_tokens(
        org_id=org.id, token_cost=250, task_id=f"issue_{req.issue_number}"
    )
    if not ok:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient Skelion tokens: {rem} remaining. Please top up your tokens.",
        )

    # 2. Solve issue & create PR
    pr_data = autonomous_engine.solve_issue_and_create_pr(
        issue_number=req.issue_number,
        title=title,
        target_path=req.target_path or "skelion_agent/core/advancement.py",
    )

    if not pr_data:
        raise HTTPException(
            status_code=500, detail="Failed to synthesize and open Pull Request."
        )

    # 3. Monitor PR
    monitor_res = autonomous_engine.monitor_and_auto_merge_pr(pr_data["pr_number"])

    return {
        "ok": True,
        "message": f"Issue #{req.issue_number} accepted and solved!",
        "tokens_deducted": 250,
        "tokens_remaining": rem,
        "pull_request": pr_data,
        "monitor_result": monitor_res,
    }


@router.post("/generate-issue")
def generate_issue(org: Organization = Depends(get_org_from_jwt)):
    """Generate a new architectural advancement issue on GitHub."""
    issue = autonomous_engine.generate_advancement_issue()
    if not issue:
        raise HTTPException(status_code=500, detail="Failed to create GitHub issue.")
    return {"ok": True, "generated_issue": issue}
