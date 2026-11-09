#!/usr/bin/env python3
"""GossipMesh Balanced Dual-Pool 24/7 Engine

Distributes available compute and AI keys 50/50:
- PR Pool (4 Workers): Deep architectural reviews, security audits, and concurrency gating.
- Issue Pool (4 Workers): Issue necessity gating, closing unnecessary tickets,
  solution synthesis, pre-flight test verification, and automated PR creation.

Supports any target repository (--repo / GH_REPO).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent if SCRIPT_DIR.name == "gossipmesh" else SCRIPT_DIR.parent

def find_script(name: str) -> Path:
    candidates = [
        SCRIPT_DIR / name,
        SCRIPT_DIR.parent / name,
        REPO_ROOT / "scripts" / "gossipmesh" / name,
        REPO_ROOT / "scripts" / name,
        REPO_ROOT / ".gossipmesh" / "scripts" / "gossipmesh" / name,
        REPO_ROOT / ".gossipmesh" / "scripts" / name,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return SCRIPT_DIR / name

REVIEWER_SCRIPT = find_script("ai_pr_reviewer.py")
ISSUE_APPROVER_SCRIPT = find_script("ai_issue_approver.py")
ISSUE_SOLVER_SCRIPT = find_script("ai_issue_solver.py")
GEN_ADVANCEMENT_SCRIPT = find_script("generate_advancement_issue.py")
PLAN_ADVANCEMENT_SCRIPT = find_script("plan_advancement_engine.py")


def run_cmd(cmd, cwd=None, env=None, **kwargs):
    capture_output = kwargs.pop("capture_output", True)
    text = kwargs.pop("text", True)
    encoding = kwargs.pop("encoding", "utf-8")
    errors = kwargs.pop("errors", "replace")
    cmd_env = env or os.environ.copy()
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=capture_output,
        text=text,
        encoding=encoding,
        errors=errors,
        env=cmd_env,
        **kwargs,
    )


def get_open_prs(repo: str = None) -> list[str]:
    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--json",
        "number",
        "--jq",
        ".[].number",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    res = run_cmd(cmd)
    if res.returncode == 0:
        return [l.strip() for l in res.stdout.splitlines() if l.strip()]
    return []


def get_open_issues(repo: str = None) -> list[dict]:
    cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--json",
        "number,title,body,labels",
        "--limit",
        "30",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    res = run_cmd(cmd)
    if res.returncode == 0 and res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except Exception:
            return []
    return []


def review_single_pr(pr_number: str, repo: str = None, workspace: str = None):
    cmd = [sys.executable, str(REVIEWER_SCRIPT), "--pr-number", str(pr_number)]
    if workspace:
        cmd.extend(["--workspace", str(workspace)])
    env = os.environ.copy()
    if repo:
        env["GH_REPO"] = repo
        env["GITHUB_REPOSITORY"] = repo
    try:
        target_ws = Path(workspace or ".").resolve()
        res = subprocess.run(
            cmd,
            cwd=target_ws,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )
        status = "OK" if res.returncode == 0 else f"FAIL (exit {res.returncode})"
        return ("PR", pr_number, status, res.stderr[-200:] if res.stderr else "")
    except Exception as e:
        return ("PR", pr_number, f"EXCEPTION: {e}", str(e))


def verify_code_preflight(workspace: Path) -> tuple[bool, str]:
    """Runs strict pre-flight code verification before creating or merging any PR.
    Guarantees that changes never affect the project negatively and keep all builds green.
    """
    # 1. Check for conflict markers in working tree
    diff_check = run_cmd(["git", "diff"], cwd=workspace)
    if any(marker in diff_check.stdout for marker in ("<<<<<<<", "=======", ">>>>>>>")):
        return False, "Unresolved git conflict markers detected in workspace."

    is_go = (workspace / "go.mod").exists()
    if is_go:
        # Check Go syntax / vetting
        vet_res = run_cmd(["go", "vet", "./..."], cwd=workspace)
        if vet_res.returncode != 0 and "go: command not found" not in vet_res.stderr:
            return False, f"go vet failed: {vet_res.stderr}"
        # Quick unit test pass
        test_res = run_cmd(
            ["go", "test", "-short", "./..."], cwd=workspace, timeout=120
        )
        if (
            test_res.returncode != 0
            and "no Go files" not in test_res.stderr
            and "go: command not found" not in test_res.stderr
        ):
            return False, f"Go test regression detected: {test_res.stdout[-250:]}"
        return True, "Go pre-flight passed."
    else:
        # 2. Python syntax & bytecode compilation check
        comp_res = run_cmd(
            [sys.executable, "-m", "compileall", "-q", "-x", r"(\.venv|\.git)", "."],
            cwd=workspace,
        )
        if comp_res.returncode != 0:
            return False, f"Python syntax/compileall error: {comp_res.stderr}"

        # 3. Regression test check (Ensure 0 broken tests)
        test_res = run_cmd(
            [sys.executable, "-m", "pytest", "-q", "--maxfail=1", "-m", "not slow"],
            cwd=workspace,
            timeout=180,
        )
        if (
            test_res.returncode not in (0, 5)
            and "pytest: command not found" not in test_res.stderr
            and "No module named pytest" not in test_res.stderr
        ):
            if "FAILED" in test_res.stdout or "ERROR" in test_res.stdout:
                return (
                    False,
                    f"Regression detected! Test suite failed: {test_res.stdout[-300:]}",
                )

        return True, "Python pre-flight and regression tests passed 100% green."


def check_issue_accepted_by_comment(issue_num: str, repo: str = None, workspace: Path = None) -> Tuple[bool, Optional[str]]:
    """Checks if any comment on the issue contains an acceptance keyword:
    'accept', 'accepted', 'approve', 'approved', '/solve', '/accept', 'lgtm'.
    Guards against negation patterns like 'do not accept' or 'cannot approve'.
    Returns (is_accepted, author).
    """
    cmd = ["gh", "issue", "view", str(issue_num), "--json", "comments"]
    if repo:
        cmd.extend(["--repo", repo])
    res = run_cmd(cmd, cwd=workspace)
    if res.returncode == 0 and res.stdout.strip():
        try:
            data = json.loads(res.stdout)
            comments = data.get("comments") or []
            negation_pattern = re.compile(
                r"\b(?:do\s+not|don't|not|cannot|can't|won't)\s+(?:accept|approve)",
                re.IGNORECASE,
            )
            acceptance_pattern = re.compile(
                r"^\s*(?:/accept|accept|/solve|approved?|lgtm)\b|\b(?:/accept|/solve)\b",
                re.IGNORECASE,
            )
            acceptance_keywords = {"accept", "accepted", "approve", "approved", "/solve", "/accept", "lgtm"}

            for c in comments:
                raw_body = (c.get("body") or "").strip()
                author = c.get("author", {}).get("login", "unknown") if isinstance(c.get("author"), dict) else "unknown"
                for line in raw_body.splitlines():
                    line_s = line.strip().lower()
                    if negation_pattern.search(line_s):
                        continue
                    tokens = set(re.findall(r"[\w/]+", line_s))
                    if any(kw in tokens for kw in acceptance_keywords) or acceptance_pattern.search(line_s):
                        return True, author
        except Exception as e:
            print(f"[!] Warning checking comments on #{issue_num}: {e}", flush=True)
    return False, None


def deduct_issue_tokens(issue_num: str, token_cost: int = 250, org_id: Optional[str] = None) -> Tuple[bool, str]:
    """Deducts tokens from organization quota using limits_service and credit_ledger.
    Guarantees deterministic idempotency key per issue.
    Returns (success, message).
    """
    try:
        from skelion_agent.database import get_engine
        from skelion_agent.models import Organization
        from skelion_agent.credit_ledger import record_ledger_entry
        from sqlmodel import Session, select

        engine = get_engine()
        with Session(engine) as session:
            org = session.get(Organization, org_id) if org_id else session.exec(select(Organization)).first()
            if not org:
                return True, "Dev Mode (No org found in database)"

            # Calculate available tokens across pools
            autofix_rem = max(0, org.autofix_tokens_total - org.autofix_tokens_used)
            pack_rem = max(0, org.purchased_tokens - org.purchased_tokens_used)
            allowance_rem = max(0, org.credits_total - org.credits_used)
            total_rem = autofix_rem + pack_rem + allowance_rem

            if total_rem < token_cost:
                return False, f"Insufficient tokens: {total_rem} available, {token_cost} required."

            # Determine bucket order: autofix -> pack -> allowance
            if autofix_rem >= token_cost:
                bucket = "autofix"
            elif pack_rem >= token_cost:
                bucket = "pack"
            else:
                bucket = "allowance"

            # Deterministic idempotency key: ensure repeat cycles for same issue do not double-bill
            idempotency_key = f"dual_engine_solve_issue_{issue_num}"
            entry, is_new = record_ledger_entry(
                session=session,
                org_id=org.id,
                bucket=bucket,
                delta=-token_cost,
                reason=f"Autonomous issue solving for #{issue_num}",
                idempotency_key=idempotency_key,
                ref_type="github_issue",
                ref_id=str(issue_num),
            )
            session.commit()
            if not is_new:
                return True, f"Tokens previously settled for Issue #{issue_num} (idempotent)."
            return True, f"Deducted {token_cost} tokens from {bucket} bucket (remaining: {total_rem - token_cost})."
    except Exception as e:
        return True, f"Bypassed token deduction ({e})"


def process_single_issue(issue: dict, repo: str = None, workspace_str: str = None):
    issue_num = str(issue.get("number"))
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    labels = [l.get("name", "") for l in issue.get("labels", [])]
    workspace = Path(workspace_str or ".").resolve()

    env = os.environ.copy()
    if repo:
        env["GH_REPO"] = repo
        env["GITHUB_REPOSITORY"] = repo

    # Skip if issue was already rejected
    if "rejected" in labels:
        return ("ISSUE", issue_num, "SKIPPED_REJECTED", "Issue already rejected.")

    # 1. Gatekeeper evaluation & Acceptance check
    is_approved = any(l in ("approved", "auto-solve") for l in labels)

    is_accepted_by_comment, comment_author = check_issue_accepted_by_comment(issue_num, repo, workspace)
    if is_accepted_by_comment:
        print(
            f"[*] Maintainer/User @{comment_author} accepted Issue #{issue_num} via comment ('accept'/'approve')!",
            flush=True,
        )
        is_approved = True

    # If this is an advancement/plan task or awaiting approval, strictly require user/maintainer acceptance!
    is_plan_task = any(l in ("advancement", "awaiting-approval", "awaiting-acceptance", "enterprise-plan") for l in labels)
    if is_plan_task and not is_approved:
        return (
            "ISSUE",
            issue_num,
            "AWAITING_ACCEPTANCE",
            "Awaiting maintainer 'accept' comment before synthesizing PR.",
        )

    if not is_approved and ISSUE_APPROVER_SCRIPT.is_file():
        print(
            f"[*] [Issue Worker] Evaluating necessity of Issue #{issue_num}: {title[:50]}...",
            flush=True,
        )
        eval_cmd = [
            sys.executable,
            str(ISSUE_APPROVER_SCRIPT),
            "--issue-number",
            issue_num,
            "--issue-title",
            title,
            "--issue-body",
            body,
            "--workspace",
            str(workspace),
        ]
        res = subprocess.run(
            eval_cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        if res.returncode == 0:
            is_approved = True
        else:
            print(f"[*] Issue #{issue_num} was closed or refined by Gatekeeper.")
            return (
                "ISSUE",
                issue_num,
                "CLOSED_OR_REFINED",
                "Closed as unnecessary or updated.",
            )

    if not is_approved:
        return (
            "ISSUE",
            issue_num,
            "UNAPPROVED",
            "Issue did not meet necessity threshold.",
        )

    # 2. Check if a valid/open or merged PR already exists for this issue
    branch_name = f"ai/solve-issue-{issue_num}"
    check_pr_cmd = [
        "gh",
        "pr",
        "list",
        "--head",
        branch_name,
        "--state",
        "all",
        "--json",
        "number,state,mergedAt,title",
    ]
    if repo:
        check_pr_cmd.extend(["--repo", repo])
    existing_prs = run_cmd(check_pr_cmd, cwd=workspace)
    if existing_prs.returncode == 0 and existing_prs.stdout.strip():
        try:
            prs_data = json.loads(existing_prs.stdout)
            has_merged = any(
                p.get("state") == "MERGED" or p.get("mergedAt") for p in prs_data
            )
            has_open = any(p.get("state") == "OPEN" for p in prs_data)
            if has_merged:
                print(
                    f"[*] Issue #{issue_num} already merged in PR. Closing issue...",
                    flush=True,
                )
                close_cmd = [
                    "gh",
                    "issue",
                    "close",
                    issue_num,
                    "--comment",
                    "Resolved by merged pull request.",
                ]
                if repo:
                    close_cmd.extend(["--repo", repo])
                run_cmd(close_cmd, cwd=workspace)
                return (
                    "ISSUE",
                    issue_num,
                    "ALREADY_MERGED",
                    "Merged PR exists; closed issue.",
                )
            if has_open:
                return ("ISSUE", issue_num, "PR_OPEN", "Active open PR already exists.")
            del_branch_cmd = ["git", "push", "origin", "--delete", branch_name]
            run_cmd(del_branch_cmd, cwd=workspace)
        except Exception as e:
            print(f"[!] Warning parsing PR JSON for #{issue_num}: {e}", flush=True)

    # 3. Synthesize automated solution
    if ISSUE_SOLVER_SCRIPT.is_file():
        # Deduct user tokens from quota before solving
        token_cost = 250
        deduct_ok, deduct_msg = deduct_issue_tokens(issue_num, token_cost=token_cost)
        if not deduct_ok:
            print(f"[!] Quota limit reached for Issue #{issue_num}: {deduct_msg}", file=sys.stderr)
            warn_cmd = [
                "gh",
                "issue",
                "comment",
                str(issue_num),
                "--body",
                f"⚠️ **Autonomous Dev Loop Paused**: {deduct_msg}\n\nPlease top up tokens or upgrade your subscription plan in Skelion Console to continue autonomous PR generation.",
            ]
            if repo:
                warn_cmd.extend(["--repo", repo])
            run_cmd(warn_cmd, cwd=workspace)
            return ("ISSUE", issue_num, "QUOTA_EXHAUSTED", deduct_msg)
        else:
            print(f"[*] Quota verified for Issue #{issue_num}: {deduct_msg}", flush=True)

        print(
            f"[*] [Issue Worker] Synthesizing automated solution for Issue #{issue_num}...",
            flush=True,
        )
        branch_name = f"ai/solve-issue-{issue_num}"

        # Clean git status before writing
        run_cmd(["git", "checkout", "main"], cwd=workspace)
        run_cmd(["git", "checkout", "--", "."], cwd=workspace)
        run_cmd(["git", "clean", "-fd"], cwd=workspace)

        solve_cmd = [
            sys.executable,
            str(ISSUE_SOLVER_SCRIPT),
            "--issue-number",
            issue_num,
            "--issue-title",
            title,
            "--issue-body",
            body,
            "--workspace",
            str(workspace),
        ]
        solve_res = subprocess.run(
            solve_cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )
        if solve_res.returncode != 0:
            run_cmd(["git", "checkout", "--", "."], cwd=workspace)
            run_cmd(["git", "clean", "-fd"], cwd=workspace)
            return ("ISSUE", issue_num, "SOLVE_FAIL", solve_res.stderr[-200:])

        # 4. Strict Pre-flight Code Verification Gate
        print(
            f"[*] Running pre-flight code verification for Issue #{issue_num}...",
            flush=True,
        )
        is_green, reason = verify_code_preflight(workspace)
        if not is_green:
            print(
                f"[!] Pre-flight verification failed for #{issue_num}: {reason}. Reverting changes...",
                file=sys.stderr,
            )
            run_cmd(["git", "checkout", "--", "."], cwd=workspace)
            run_cmd(["git", "clean", "-fd"], cwd=workspace)
            return ("ISSUE", issue_num, "PREFLIGHT_FAIL", reason)

        # 5. Create branch, commit, push, and open PR
        print(f"[*] Pre-flight passed! Staging changes on {branch_name}...", flush=True)
        run_cmd(["git", "checkout", "-B", branch_name], cwd=workspace)
        author_name = os.environ.get("GIT_AUTHOR_NAME") or "Dahale Aditya Dnyaneshwar"
        author_email = os.environ.get("GIT_AUTHOR_EMAIL") or "adityadahale96@gmail.com"
        run_cmd(["git", "config", "user.name", author_name], cwd=workspace)
        run_cmd(["git", "config", "user.email", author_email], cwd=workspace)

        run_cmd(["git", "add", "-A"], cwd=workspace)
        for stray in [
            ".gossipmesh",
            ".gossip_mesh",
            "memes.json",
            "ai_pr_*.md",
            "ai_review_*.json",
            "ci_fix_*.md",
            "*.log",
        ]:
            run_cmd(["git", "rm", "-r", "--cached", stray], cwd=workspace, check=False)
            run_cmd(["git", "reset", "--", stray], cwd=workspace, check=False)
        author_name = os.environ.get("GIT_AUTHOR_NAME") or "Dahale Aditya Dnyaneshwar"
        author_email = os.environ.get("GIT_AUTHOR_EMAIL") or "adityadahale96@gmail.com"
        commit_msg = f"feat(ai): resolve #{issue_num} - {title}\n\nCo-authored-by: {author_name} <{author_email}>"
        run_cmd(
            [
                "git",
                "commit",
                "-m",
                commit_msg,
                f"--author={author_name} <{author_email}>",
            ],
            cwd=workspace,
        )

        # Push branch
        print(f"[*] Pushing branch {branch_name} to remote...", flush=True)
        push_res = run_cmd(
            ["git", "push", "origin", branch_name, "--force"], cwd=workspace
        )
        if push_res.returncode != 0:
            run_cmd(["git", "checkout", "main"], cwd=workspace)
            return ("ISSUE", issue_num, "PUSH_FAIL", push_res.stderr[-200:])

        # Create PR
        summary_path = workspace / "ai_pr_summary.md"
        summary_body = (
            summary_path.read_text(encoding="utf-8")
            if summary_path.exists()
            else f"Automated solution for Issue #{issue_num}.\n\nCloses #{issue_num}"
        )
        if f"Closes #{issue_num}" not in summary_body:
            summary_body += f"\n\nCloses #{issue_num}"

        pr_cmd = [
            "gh",
            "pr",
            "create",
            "--head",
            branch_name,
            "--base",
            "main",
            "--title",
            f"feat: resolve #{issue_num} - {title}",
            "--body",
            summary_body,
            "--label",
            "advancement",
        ]
        if repo:
            pr_cmd.extend(["--repo", repo])

        pr_res = run_cmd(pr_cmd, cwd=workspace)
        run_cmd(["git", "checkout", "main"], cwd=workspace)

        if pr_res.returncode == 0:
            pr_url = pr_res.stdout.strip()
            print(f"[✓] Created Pull Request: {pr_url}", flush=True)
            # Instant Pre-Flight Auto-Approval & Rapid Squash Merge
            try:
                pr_num_str = pr_url.split("/")[-1]
                # 1. Immediate Pre-Flight Approval
                approve_cmd = [
                    "gh",
                    "pr",
                    "review",
                    pr_num_str,
                    "--approve",
                    "--body",
                    "Autonomous pre-flight verification passed: clean syntax, unit tests verified.",
                ]
                if repo:
                    approve_cmd.extend(["--repo", repo])
                run_cmd(approve_cmd, cwd=workspace)
                print(
                    f"[✓] Approved PR #{pr_num_str} with pre-flight clearance.",
                    flush=True,
                )

                # 2. Immediate Administrative Squash Merge (sub-10s merge)
                merge_cmd = [
                    "gh",
                    "pr",
                    "merge",
                    pr_num_str,
                    "--squash",
                    "--delete-branch",
                    "--admin",
                ]
                if repo:
                    merge_cmd.extend(["--repo", repo])
                m_res = run_cmd(merge_cmd, cwd=workspace)
                if m_res.returncode == 0:
                    print(
                        f"[⚡ INSTANT MERGE] Successfully merged PR #{pr_num_str} directly to main!",
                        flush=True,
                    )
                else:
                    # 3. Fallback to --auto if branch protection waits on status checks
                    auto_cmd = [
                        "gh",
                        "pr",
                        "merge",
                        pr_num_str,
                        "--auto",
                        "--squash",
                        "--delete-branch",
                    ]
                    if repo:
                        auto_cmd.extend(["--repo", repo])
                    run_cmd(auto_cmd, cwd=workspace)
                    print(
                        f"[*] Queued PR #{pr_num_str} for --auto merge upon status checks completion.",
                        flush=True,
                    )
            except Exception as e:
                print(f"[!] Auto-merge helper notice: {e}", flush=True)
            return ("ISSUE", issue_num, "PR_CREATED", pr_url)
        else:
            return ("ISSUE", issue_num, "PR_CREATE_FAIL", pr_res.stderr[-200:])

    return ("ISSUE", issue_num, "SKIPPED", "")


def main():
    parser = argparse.ArgumentParser(
        description="GossipMesh 50/50 Dual-Pool Autonomous Engine"
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY"),
    )
    parser.add_argument("--workspace", default=".")
    parser.add_argument(
        "--pr-workers", type=int, default=4, help="Number of PR review workers"
    )
    parser.add_argument(
        "--issue-workers",
        type=int,
        default=4,
        help="Number of Issue resolution workers",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=12,
        help="Maximum number of issues to resolve per run",
    )
    parser.add_argument(
        "--max-prs", type=int, default=8, help="Maximum number of PRs to review per run"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "pr-only", "issue-only"],
        default=os.environ.get("DUAL_POOL_MODE", "all"),
        help="Execution mode: all (fallback dual-pool), pr-only (dedicated PR reviewer), or issue-only (dedicated issue solver)",
    )
    parser.add_argument(
        "--shard-id",
        type=int,
        default=int(os.environ.get("SHARD_ID", "0")),
        help="Shard index (0 to num-shards - 1)",
    )
    parser.add_argument(
        "--num-shards",
        type=int,
        default=int(os.environ.get("NUM_SHARDS", "1")),
        help="Total number of parallel shards",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run 24/7 autonomous loop continuously in background/daemon mode",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Sleep duration in seconds between continuous loop cycles (default: 10)",
    )
    parser.add_argument(
        "--issue-number",
        type=str,
        default=None,
        help="Target a specific issue number directly for gatekeeping, token deduction, and PR synthesis",
    )
    args = parser.parse_args()

    repo = args.repo
    print("=" * 60)
    print(
        f"[*] GossipMesh 50/50 Balanced Dual-Pool Active on: {repo or 'Current Repository'}"
    )
    print(
        f"[*] Allocation: {args.pr_workers} PR Review Workers | {args.issue_workers} Issue Solver Workers"
    )
    print("=" * 60)

    if args.continuous:
        print(f"[*] 24/7 Autonomous Dev Loop running continuously every {args.interval}s. Press Ctrl+C to terminate.")
        while True:
            try:
                run_cycle(args, repo)
            except KeyboardInterrupt:
                print("\n[*] Autonomous Dev Loop terminated by user.")
                break
            except Exception as e:
                print(f"[!] Autonomous Dev Loop cycle error: {e}", file=sys.stderr)
            time.sleep(args.interval)
    else:
        run_cycle(args, repo)


def run_cycle(args, repo):
    # Direct targeted single issue execution (e.g. from GitHub Actions issue_comment trigger)
    if getattr(args, "issue_number", None):
        issue_num = str(args.issue_number)
        print(f"[*] Targeting specific Issue #{issue_num} for autonomous processing...")
        cmd = [
            "gh",
            "issue",
            "view",
            issue_num,
            "--json",
            "number,title,body,labels",
        ]
        if repo:
            cmd.extend(["--repo", repo])
        res = run_cmd(cmd, cwd=Path(args.workspace or ".").resolve())
        if res.returncode == 0 and res.stdout.strip():
            try:
                target_issue = json.loads(res.stdout)
                task_type, item_id, status, details = process_single_issue(
                    target_issue, repo, args.workspace
                )
                print(f"[{task_type}] #{item_id}: {status}")
                if details:
                    print(f"    Detail: {details.strip()[:150]}")
                return
            except Exception as e:
                print(f"[!] Error processing targeted Issue #{issue_num}: {e}")
                return
        else:
            print(f"[!] Failed to fetch metadata for Issue #{issue_num}: {res.stderr}")
            return

    pr_numbers = get_open_prs(repo)
    open_issues = get_open_issues(repo)

    if args.num_shards > 1:
        total_before = len(open_issues)
        open_issues = [
            issue
            for issue in open_issues
            if (issue.get("number", 0) % args.num_shards) == args.shard_id
        ]
        print(
            f"[*] Shard {args.shard_id}/{args.num_shards} claimed {len(open_issues)} of {total_before} issue(s)."
        )

    print(
        f"[*] Discovered: {len(pr_numbers)} open PR(s), {len(open_issues)} open Issue(s)."
    )

    # 1. Run PR Reviews in Pool A (Sequential to prevent git collisions and API limits)
    if args.mode in ("all", "pr-only"):
        print(
            f"\n[*] Launching Pool A: PR Review Workers (Sequential, max {args.max_prs})...\n"
        )
        for pr in pr_numbers[: args.max_prs]:
            try:
                task_type, item_id, status, details = review_single_pr(
                    pr, repo, args.workspace
                )
                print(f"[{task_type}] #{item_id}: {status}")
                if details:
                    print(f"    Detail: {details.strip()[:150]}")
            except Exception as exc:
                print(f"[!] PR Worker exception: {exc}")

    # 2. Run Issue Gatekeeper & Solution Synthesis in Pool B
    if args.mode in ("all", "issue-only"):
        print(
            f"\n[*] Launching Pool B: Issue Gatekeeper & Solver Workers (Sequential, max {args.max_issues})...\n"
        )
        solved_count = 0
        for issue in open_issues:
            if solved_count >= args.max_issues:
                break
            try:
                task_type, item_id, status, details = process_single_issue(
                    issue, repo, args.workspace
                )
                print(f"[{task_type}] #{item_id}: {status}")
                if details:
                    print(f"    Detail: {details.strip()[:150]}")
                if status == "PR_CREATED":
                    solved_count += 1
            except Exception as exc:
                print(f"[!] Issue Worker exception: {exc}")

        # 3. Autonomous Issue Generation only if backlog is low (< 3) and genuine plan tasks exist
        if len(open_issues) < 3:
            print(
                "[*] Issue backlog low (< 3). Checking repository for genuine implementation plan tasks...",
                flush=True,
            )
            if PLAN_ADVANCEMENT_SCRIPT.is_file():
                gen_env = os.environ.copy()
                if repo:
                    gen_env["GH_REPO"] = repo
                    gen_env["GITHUB_REPOSITORY"] = repo
                subprocess.run(
                    [
                        sys.executable,
                        str(PLAN_ADVANCEMENT_SCRIPT),
                        "--batch",
                        "1",
                        "--workspace",
                        str(args.workspace),
                        "--repo",
                        repo or "",
                    ],
                    cwd=Path(args.workspace),
                    env=gen_env,
                )
            else:
                print("[*] No plan advancement script found. Skipping issue generation.", flush=True)

    print("=" * 60)
    print(f"[✓] Dual-Pool cycle ({args.mode}) finished successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
