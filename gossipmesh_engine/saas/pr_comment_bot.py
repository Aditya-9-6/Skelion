# gossipmesh/saas/pr_comment_bot.py
"""Webhook handler for PR comment bot.
Listens for GitHub pull_request events and posts a comment requesting missing information.
This is a minimal stub – you can extend the logic as needed.
"""

from fastapi import APIRouter, Request, HTTPException
import json
import subprocess
import os

router = APIRouter()

@router.post("/pull_request")
async def handle_pull_request(request: Request):
    """Handle GitHub pull_request webhook events.
    Expected payload structure follows GitHub's webhook schema.
    If the PR body is empty or missing required fields, a comment is posted via the `gh` CLI.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Only act on opened or reopened PRs
    action = payload.get("action")
    if action not in {"opened", "reopened"}:
        return {"status": "ignored", "reason": f"action {action} not relevant"}

    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    body = pr.get("body", "").strip()
    repo_full_name = payload.get("repository", {}).get("full_name")

    # Simple validation: require a non‑empty description and a link to an issue
    if not body or "#" not in body:
        comment = (
            "👋 Hi! It looks like this PR is missing a clear description or linked issue. "
            "Please add a concise summary and reference the related GitHub issue (e.g., `Fixes #123`)."
        )
        # Use gh CLI to comment – requires GH_TOKEN env var with appropriate scopes
        cmd = [
            "gh",
            "pr",
            "comment",
            str(pr_number),
            "--repo",
            repo_full_name,
            "--body",
            comment,
        ]
        # Execute command; capture any error for debugging
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to post comment: {result.stderr.strip()}",
            )
        return {"status": "commented", "pr": pr_number}

    # If everything looks fine, do nothing
    return {"status": "ok", "pr": pr_number}
