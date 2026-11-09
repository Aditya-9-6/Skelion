# skelion_agent/pr_review_publisher.py — PR Review Publisher Helpers
"""
PR Review Publisher Helpers:
- Generates inline GitHub suggestion blocks (```suggestion ... ```).
- Renders comprehensive review comments with Evidence Bundle cards.
- Handles one-click commit and one-click revert workflows:
  - Command parsing: `@skelion revert <run_id>`
  - Unified diff inversion.
  - Automated commit & revert execution.
"""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from skelion_agent.pr_review_fixer import FixFinding, FixSuggestion
from skelion_agent.pr_review_verifier import EvidenceBundle, Verdict


@dataclass
class CommitResult:
    """Result of a one-click commit operation."""
    success: bool
    run_id: str
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "run_id": self.run_id,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "error": self.error,
        }


@dataclass
class RevertResult:
    """Result of a one-click revert operation."""
    success: bool
    run_id: str
    revert_commit_sha: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "run_id": self.run_id,
            "revert_commit_sha": self.revert_commit_sha,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Inline Suggestion & Comment Formatting
# ---------------------------------------------------------------------------

def format_github_suggestion_block(replacement_code: str) -> str:
    """
    Wraps replacement code inside a GitHub suggestion markdown block.
    """
    clean_replacement = replacement_code.rstrip("\r\n")
    return f"```suggestion\n{clean_replacement}\n```"


def extract_replacement_from_diff(diff_text: str) -> str:
    """
    Extracts the replacement code lines from a unified diff hunk
    by selecting all '+' lines and unchanged ' ' lines, skipping headers.
    """
    replacement_lines: List[str] = []
    in_hunk = False

    for line in diff_text.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            replacement_lines.append(line[1:])
        elif line.startswith(" "):
            replacement_lines.append(line[1:])
        # Skip '-' lines

    return "\n".join(replacement_lines)


def format_pr_review_comment(
    finding: FixFinding,
    fix: FixSuggestion,
    evidence_bundle: Union[EvidenceBundle, Dict[str, Any]],
    run_id: Optional[str] = None,
) -> str:
    """
    Constructs an inline GitHub PR review comment featuring:
    1. Finding details & severity badge.
    2. Evidence bundle summary & verification verdict.
    3. Inline GitHub suggestion block.
    4. One-click revert command instructions (@skelion revert <run_id>).
    """
    bundle_dict = evidence_bundle.to_dict() if hasattr(evidence_bundle, "to_dict") else evidence_bundle
    verdict_str = bundle_dict.get("verdict", "unverified").upper()
    diff_hash = bundle_dict.get("diff_hash", fix.diff_hash)[:12]
    effective_run_id = run_id or fix.metadata.get("run_id") or fix.id

    # Format verdict badge
    if verdict_str == "VERIFIED":
        badge = "🟢 **VERIFIED**"
    elif verdict_str == "VERIFIED WITH GAPS":
        badge = "🟡 **VERIFIED WITH GAPS**"
    else:
        badge = "🔴 **UNVERIFIED**"

    # Extract suggestion code
    suggestion_code = extract_replacement_from_diff(fix.diff)

    test_counts = bundle_dict.get("test_counts", {})
    before_tests = test_counts.get("before", {}).get("passed", 0)
    after_tests = test_counts.get("after", {}).get("passed", 0)
    regressions = test_counts.get("regressions", 0)

    gaps_section = ""
    gaps = bundle_dict.get("gaps", [])
    if gaps:
        gaps_list = "\n".join(f"  - ⚠️ *{g}*" for g in gaps)
        gaps_section = f"\n**Noted Gaps:**\n{gaps_list}\n"

    comment = f"""### 🛡️ Skelion Autofix ({fix.fix_type.value}) — {badge}

**Finding:** `{finding.rule_id or finding.id}` | **Severity:** `{finding.severity}`
> {finding.message}

{format_github_suggestion_block(suggestion_code)}

<details>
<summary>📋 <b>Evidence Bundle Summary</b> (Diff: <code>{diff_hash}</code>)</summary>

- **Verdict:** `{verdict_str}`
- **Diff Budget:** {fix.lines_changed} lines changed across {len(fix.file_paths)} file(s)
- **Regression Check:** {after_tests} tests passed (baseline: {before_tests}, regressions: **{regressions}**)
{gaps_section}
</details>

---
*💡 Click **Commit suggestion** to apply this patch. To undo at any time, comment:*
`@skelion revert {effective_run_id}`
"""
    return comment.strip()


# ---------------------------------------------------------------------------
# Revert Command Parsing & Diff Inversion
# ---------------------------------------------------------------------------

REVERT_COMMAND_REGEX = re.compile(
    r"@skelion\s+revert\s+<?([A-Za-z0-9_\-\.]+)?>?",
    re.IGNORECASE,
)


def parse_revert_command(comment_text: str) -> Optional[str]:
    """
    Parses a user PR comment to check for '@skelion revert <run_id>' or '@skelion revert run_id'.
    Returns the target run_id if matched, otherwise None.
    """
    match = REVERT_COMMAND_REGEX.search(comment_text)
    if match and match.group(1):
        return match.group(1).strip()
    return None


def invert_unified_diff(diff_text: str) -> str:
    """
    Inverts a unified diff so that applying it reverses the original patch:
    - Swaps '--- a/path' and '+++ b/path'
    - Replaces '+' with '-' and '-' with '+'
    - Adjusts hunk header counts @@ -old,old_cnt +new,new_cnt @@
    """
    if not diff_text.strip():
        return ""

    inverted_lines: List[str] = []
    lines = diff_text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("--- "):
            # Check next line for +++
            if i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
                from_line = line[4:]
                to_line = lines[i + 1][4:]
                inverted_lines.append(f"--- {to_line}")
                inverted_lines.append(f"+++ {from_line}")
                i += 2
                continue
            else:
                inverted_lines.append(line)
        elif line.startswith("@@"):
            # Invert hunk header: @@ -old,cnt +new,cnt @@ -> @@ -new,cnt +old,cnt @@
            hunk_match = re.match(r"^@@\s*-(\d+(?:,\d+)?)\s+\+(\d+(?:,\d+)?)\s*@@(.*)$", line)
            if hunk_match:
                old_part = hunk_match.group(1)
                new_part = hunk_match.group(2)
                rest = hunk_match.group(3)
                inverted_lines.append(f"@@ -{new_part} +{old_part} @@{rest}")
            else:
                inverted_lines.append(line)
        elif line.startswith("+") and not line.startswith("+++"):
            inverted_lines.append("-" + line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            inverted_lines.append("+" + line[1:])
        else:
            inverted_lines.append(line)

        i += 1

    return "\n".join(inverted_lines) + ("\n" if diff_text.endswith("\n") else "")


# ---------------------------------------------------------------------------
# One-Click Commit and Revert Execution
# ---------------------------------------------------------------------------

def apply_one_click_commit(
    repo_path: Path | str,
    run_id: str,
    diff: str,
    branch: Optional[str] = None,
    author_name: str = "skelion-bot",
    author_email: str = "bot@skelion.dev",
) -> CommitResult:
    """
    Applies a verified patch directly to the repo and creates a git commit.
    """
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return CommitResult(success=False, run_id=run_id, error=f"Repo path '{repo}' does not exist")

    # Invert/apply patch
    patch_file = repo / f".skelion_commit_{uuid.uuid4().hex[:6]}.patch"
    try:
        patch_file.write_text(diff, encoding="utf-8")
        # Apply patch via git apply
        res_apply = subprocess.run(
            ["git", "apply", "--whitespace=fix", str(patch_file)],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res_apply.returncode != 0:
            # Fallback with ignore-whitespace
            res_apply = subprocess.run(
                ["git", "apply", "--ignore-whitespace", str(patch_file)],
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=15,
            )

        if res_apply.returncode != 0:
            return CommitResult(
                success=False,
                run_id=run_id,
                error=f"git apply failed: {res_apply.stderr}",
            )

        # Stage and commit
        subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True, timeout=10)

        commit_msg = f"fix(skelion): apply verified fix [run_id: {run_id}]"
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = author_name
        env["GIT_AUTHOR_EMAIL"] = author_email
        env["GIT_COMMITTER_NAME"] = author_name
        env["GIT_COMMITTER_EMAIL"] = author_email

        res_commit = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(repo),
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if res_commit.returncode != 0:
            # Might be empty commit or error
            return CommitResult(
                success=False,
                run_id=run_id,
                error=f"git commit failed: {res_commit.stderr or res_commit.stdout}",
            )

        # Retrieve commit SHA
        rev_res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit_sha = rev_res.stdout.strip() if rev_res.returncode == 0 else "HEAD"

        return CommitResult(
            success=True,
            run_id=run_id,
            commit_sha=commit_sha,
            branch=branch,
        )

    except Exception as e:
        return CommitResult(success=False, run_id=run_id, error=str(e))

    finally:
        if patch_file.exists():
            try:
                patch_file.unlink()
            except Exception:
                pass


def execute_one_click_revert(
    repo_path: Path | str,
    run_id: str,
    original_diff: Optional[str] = None,
    commit_sha: Optional[str] = None,
    author_name: str = "skelion-bot",
    author_email: str = "bot@skelion.dev",
) -> RevertResult:
    """
    Reverts a previously applied fix using either git revert on the commit SHA
    or by generating and applying an inverted unified diff.
    """
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return RevertResult(success=False, run_id=run_id, error=f"Repo path '{repo}' does not exist")

    # Strategy 1: Git revert by commit SHA
    if commit_sha:
        try:
            env = os.environ.copy()
            env["GIT_AUTHOR_NAME"] = author_name
            env["GIT_AUTHOR_EMAIL"] = author_email
            env["GIT_COMMITTER_NAME"] = author_name
            env["GIT_COMMITTER_EMAIL"] = author_email

            res = subprocess.run(
                ["git", "revert", "--no-edit", commit_sha],
                cwd=str(repo),
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if res.returncode == 0:
                rev_res = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(repo),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                new_sha = rev_res.stdout.strip() if rev_res.returncode == 0 else None
                return RevertResult(success=True, run_id=run_id, revert_commit_sha=new_sha)
            elif not original_diff:
                return RevertResult(success=False, run_id=run_id, error=f"git revert failed: {res.stderr or res.stdout}")
        except Exception as e:
            if not original_diff:
                return RevertResult(success=False, run_id=run_id, error=str(e))

    # Strategy 2: Inverted diff application
    if original_diff:
        try:
            inv_diff = invert_unified_diff(original_diff)
            patch_file = repo / f".skelion_revert_{uuid.uuid4().hex[:6]}.patch"
            patch_file.write_text(inv_diff, encoding="utf-8")

            try:
                res_apply = subprocess.run(
                    ["git", "apply", "--whitespace=fix", str(patch_file)],
                    cwd=str(repo),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if res_apply.returncode != 0:
                    res_apply = subprocess.run(
                        ["git", "apply", "--ignore-whitespace", str(patch_file)],
                        cwd=str(repo),
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )

                if res_apply.returncode != 0:
                    return RevertResult(
                        success=False,
                        run_id=run_id,
                        error=f"Inverse git apply failed: {res_apply.stderr}",
                    )

                subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True, timeout=10)
                revert_msg = f"revert(skelion): revert fix for run {run_id}"

                env = os.environ.copy()
                env["GIT_AUTHOR_NAME"] = author_name
                env["GIT_AUTHOR_EMAIL"] = author_email
                env["GIT_COMMITTER_NAME"] = author_name
                env["GIT_COMMITTER_EMAIL"] = author_email

                res_commit = subprocess.run(
                    ["git", "commit", "-m", revert_msg],
                    cwd=str(repo),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

                rev_res = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(repo),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                new_sha = rev_res.stdout.strip() if rev_res.returncode == 0 else None

                return RevertResult(success=True, run_id=run_id, revert_commit_sha=new_sha)

            finally:
                if patch_file.exists():
                    try:
                        patch_file.unlink()
                    except Exception:
                        pass

        except Exception as e:
            return RevertResult(success=False, run_id=run_id, error=str(e))

    return RevertResult(
        success=False,
        run_id=run_id,
        error="Neither valid commit_sha nor original_diff provided for revert",
    )
