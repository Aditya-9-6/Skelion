# skelion_agent/pr_review_orchestrator.py — PR Review Multi-Lane Orchestrator & GitHub Bot
"""
PR Review Orchestrator:
- Manages in-place comment updates to avoid PR comment spam.
- Enforces credit cap & BYO-AI zero-debit rules.
- Formats runtime lane statistics or clean skip notices.
- Detects resolved thread regressions ("still present after resolution").
- Handles GitHub API secondary rate limits with exponential backoff.
"""

from __future__ import annotations

import time
import math
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class CommentUpdateResult:
    action: str  # "created" or "updated_in_place"
    comment_id: str
    body: str
    was_edited: bool = False


def post_or_update_pr_summary(
    pr_number: int,
    head_sha: str,
    summary_content: str,
    existing_comment_id: Optional[str] = None,
    github_client: Optional[Any] = None,
) -> CommentUpdateResult:
    """
    Updates existing summary comment in-place if comment_id is known,
    otherwise posts a new summary comment. Avoids PR comment spam.
    """
    formatted_body = (
        f"<!-- skelion-pr-review-summary -->\n"
        f"### 🛡️ Skelion Review Report — Commit `{head_sha[:8]}`\n\n"
        f"{summary_content}\n\n"
        f"_Last updated for `{head_sha}`_"
    )

    if existing_comment_id:
        # Edit comment in-place
        if github_client and hasattr(github_client, "update_comment"):
            github_client.update_comment(existing_comment_id, formatted_body)
        return CommentUpdateResult(
            action="updated_in_place",
            comment_id=existing_comment_id,
            body=formatted_body,
            was_edited=True,
        )
    else:
        new_id = f"comment_summary_{pr_number}"
        if github_client and hasattr(github_client, "create_comment"):
            resp = github_client.create_comment(pr_number, formatted_body)
            if isinstance(resp, dict) and "id" in resp:
                new_id = str(resp["id"])
        return CommentUpdateResult(
            action="created",
            comment_id=new_id,
            body=formatted_body,
            was_edited=False,
        )


def post_or_update_inline_comments(
    pr_number: int,
    head_sha: str,
    findings: List[Any],
    existing_inline_comments: Optional[Dict[str, str]] = None,
    github_client: Optional[Any] = None,
) -> List[CommentUpdateResult]:
    """
    Publishes or updates inline review comments in-place on subsequent PR pushes.
    Maps findings by fingerprint to avoid duplicate comment spam across commits.
    """
    results: List[CommentUpdateResult] = []
    existing = dict(existing_inline_comments or {})

    for idx, f in enumerate(findings):
        fp = getattr(f, "fingerprint", None) or f"{getattr(f, 'file_path', 'unknown')}:{getattr(f, 'line_number', 0)}"
        file_path = getattr(f, "file_path", "unknown")
        line = getattr(f, "line_number", 1)
        msg = getattr(f, "message", "Finding")
        body = (
            f"<!-- skelion-inline:{fp} -->\n"
            f"**Finding**: {msg}\n\n"
            f"_Updated in-place for commit `{head_sha[:8]}`_"
        )

        if fp in existing:
            comment_id = existing[fp]
            if github_client and hasattr(github_client, "update_inline_comment"):
                github_client.update_inline_comment(comment_id, body)
            results.append(
                CommentUpdateResult(
                    action="updated_in_place",
                    comment_id=comment_id,
                    body=body,
                    was_edited=True,
                )
            )
        else:
            new_id = f"comment_inline_{pr_number}_{idx + 1}"
            if github_client and hasattr(github_client, "create_inline_comment"):
                resp = github_client.create_inline_comment(pr_number, file_path, line, body)
                if isinstance(resp, dict) and "id" in resp:
                    new_id = str(resp["id"])
            results.append(
                CommentUpdateResult(
                    action="created",
                    comment_id=new_id,
                    body=body,
                    was_edited=False,
                )
            )

    return results


@dataclass
class CreditEvaluationResult:
    deterministic_only: bool
    ai_lane_enabled: bool
    credits_debited_milli: int
    provider_cost_cents: float
    summary_note: Optional[str] = None


def evaluate_credit_cap_and_byo(
    plan_tier: str,
    credit_budget_milli: Optional[int],
    estimated_milli: int,
    active_lanes: List[str],
) -> CreditEvaluationResult:
    """
    Evaluates per-PR credit cap and BYO-AI pricing.
    - If BYO-AI: zero credits debited, zero provider cost.
    - If credit cap exceeded: runs deterministic lanes only, notes cap in summary.
    """
    is_byo = plan_tier.lower() in ("byo_ai", "byok", "enterprise_byo")

    if is_byo:
        return CreditEvaluationResult(
            deterministic_only=False,
            ai_lane_enabled=True,
            credits_debited_milli=0,
            provider_cost_cents=0.0,
            summary_note="BYO-AI mode active: 0 credits debited, provider billed directly.",
        )

    # Check credit budget / cap
    if credit_budget_milli is not None and estimated_milli > credit_budget_milli:
        return CreditEvaluationResult(
            deterministic_only=True,
            ai_lane_enabled=False,
            credits_debited_milli=0,
            provider_cost_cents=0.0,
            summary_note=(
                f"Per-PR credit cap reached: estimated {estimated_milli} mCredits "
                f"exceeds budget {credit_budget_milli} mCredits. "
                "Skipped LLM review; ran deterministic lanes only."
            ),
        )

    return CreditEvaluationResult(
        deterministic_only=False,
        ai_lane_enabled=True,
        credits_debited_milli=estimated_milli,
        provider_cost_cents=round(estimated_milli * 0.001, 4),
        summary_note=None,
    )


def render_runtime_lane_summary(metrics: Optional[Dict[str, Any]]) -> str:
    """
    Renders runtime observability card.
    If no runtime data exists, outputs 'skipped: no runtime data' with zero invented numbers.
    If metrics exist, reports traffic share, observation window, error rate, and source.
    """
    if not metrics or not metrics.get("has_data", False):
        return "skipped: no runtime data"

    traffic_share = metrics.get("traffic_share", 0.0)
    window = metrics.get("window", "7d")
    error_rate = metrics.get("error_rate", 0.0)
    source = metrics.get("source", "Telemetry Mesh")

    traffic_share_pct = f"{traffic_share * 100:.1f}%" if traffic_share < 1.0 else f"{traffic_share:.1f}%"
    error_rate_pct = f"{error_rate * 100:.2f}%" if error_rate < 1.0 else f"{error_rate:.2f}%"

    return (
        f"**Runtime Telemetry**:\n"
        f"- Traffic Share: {traffic_share_pct}\n"
        f"- Window: {window}\n"
        f"- Error Rate: {error_rate_pct}\n"
        f"- Source: {source}"
    )


def check_resolved_thread_reappearance(
    resolved_fingerprints: Set[str],
    current_findings: List[Any],
) -> List[Tuple[Any, str]]:
    """
    Flags any finding whose fingerprint was previously marked resolved.
    Returns list of (finding, note).
    """
    flagged = []
    for f in current_findings:
        fp = getattr(f, "fingerprint", "")
        if fp and fp in resolved_fingerprints:
            flagged.append((f, "still present after resolution"))
    return flagged


class SecondaryRateLimitError(Exception):
    """Raised when GitHub returns 403/429 secondary rate limit."""
    def __init__(self, message: str = "Secondary rate limit", retry_after: float = 0.05):
        super().__init__(message)
        self.retry_after = retry_after


def publish_comments_with_backoff(
    comments: List[Dict[str, Any]],
    poster_fn: Callable[[Dict[str, Any]], bool],
    max_retries: int = 4,
    base_backoff_sec: float = 0.01,
) -> Dict[str, Any]:
    """
    Publishes comments to GitHub with exponential backoff on secondary rate limits (403/429).
    Guarantees no lost comments when transient rate limits are encountered.
    """
    published = []
    failed = []

    for item in comments:
        success = False
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                ok = poster_fn(item)
                if ok:
                    published.append(item)
                    success = True
                    break
            except SecondaryRateLimitError as err:
                last_err = err
                # Exponential backoff with retry
                backoff = base_backoff_sec * (2 ** attempt)
                time.sleep(backoff)
            except Exception as e:
                last_err = e
                break

        if not success:
            failed.append({"comment": item, "error": str(last_err)})

    return {
        "published_count": len(published),
        "failed_count": len(failed),
        "published": published,
        "failed": failed,
        "no_lost_comments": len(failed) == 0,
    }
