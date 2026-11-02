# skelion_agent/sync_routes.py — REST Endpoints for Cross-Repo Auto-Sync
"""
Endpoints:
- GET  /v1/sync/status: Check upstream DevProxy & GossipMesh sync status and pending commits.
- POST /v1/sync/trigger: Trigger immediate cross-repo synchronization cycle.
- POST /v1/sync/webhook: GitHub Webhook handler for instant upstream push events.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel

from skelion_agent.models import Organization
from skelion_agent.auth_routes import get_org_from_jwt
from skelion_agent.cross_repo_syncer import cross_repo_syncer

router = APIRouter(prefix="/v1/sync", tags=["Cross-Repo Upstream Auto-Sync"])


class TriggerSyncRequest(BaseModel):
    repo: Optional[str] = None
    force: Optional[bool] = False


@router.get("/status")
def get_sync_status(org: Organization = Depends(get_org_from_jwt)):
    """Return status of upstream repositories (DevProxy & GossipMesh) and sync history."""
    updates = cross_repo_syncer.check_updates()
    return {
        "ok": True,
        "upstreams": updates,
        "state": cross_repo_syncer.state,
        "history": cross_repo_syncer.state.get("history", [])[-15:],
    }


@router.post("/trigger")
def trigger_sync(
    req: Optional[TriggerSyncRequest] = None,
    org: Organization = Depends(get_org_from_jwt),
):
    """
    Triggers cross-repository synchronization:
    - If clean: directly merges to main.
    - If conflicts exist: opens PR and notifies autonomous conflict agent.
    """
    force = req.force if req else False
    target_repo = req.repo if req else None

    if target_repo:
        if target_repo not in ("devproxy", "gossipmesh"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid repo: {target_repo}. Choose 'devproxy' or 'gossipmesh'.",
            )
        result = cross_repo_syncer.sync_repository(target_repo, force=force)
        return {"ok": True, "repo": target_repo, "result": result}

    full_res = cross_repo_syncer.run_full_sync(force=force)
    return {"ok": True, "summary": full_res}


@router.post("/webhook")
async def github_upstream_webhook(
    request: Request, x_github_event: Optional[str] = Header(None)
):
    """
    Webhook receiver for GitHub push events from DevProxy or GossipMesh.
    Automatically triggers cross-repository synchronization in real-time.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    repo_data = body.get("repository", {})
    repo_name = repo_data.get("name", "").lower()

    target_key = None
    if "devproxy" in repo_name:
        target_key = "devproxy"
    elif "gossipmesh" in repo_name:
        target_key = "gossipmesh"

    if target_key:
        cross_repo_syncer.log(
            f"Received GitHub Webhook push event from {repo_name}! Triggering auto-sync..."
        )
        res = cross_repo_syncer.sync_repository(target_key, force=True)
        return {
            "ok": True,
            "event": "sync_triggered",
            "repo": target_key,
            "result": res,
        }

    return {
        "ok": True,
        "event": "ignored",
        "reason": f"Repo {repo_name} not configured for auto-sync",
    }
