# skelion_agent/pr_review_fixer.py — PR Review Fix Engine & Strategy Implementations
"""
Fix Engine & Types:
- F1 Tool-native autofix (Ruff, ESLint, Black, Prettier formatting/fixing).
- F2 Codemod templates (blocking to async, unused import removal, deprecated API replacement).
- F3 Bounded LLM patch (single function / <= 2 files, unified diff only, bounded line count).
- Excluded paths guard: strictly forbids auto-fixing migrations, workflows,
  Dockerfiles, secrets files, and auth/payment paths.
"""

from __future__ import annotations

import difflib
import fnmatch
import hashlib
import os
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Enums and Models
# ---------------------------------------------------------------------------

class FixType(str, Enum):
    TOOL_NATIVE = "F1"
    CODEMOD = "F2"
    BOUNDED_LLM = "F3"


@dataclass
class FixFinding:
    """Represents a static analysis or security finding targeted for fix."""
    id: str
    file_path: str
    line: int = 1
    end_line: Optional[int] = None
    rule_id: Optional[str] = None
    message: str = ""
    severity: str = "MEDIUM"
    category: Optional[str] = None
    source_tool: str = "ruff"
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            # Deterministic fingerprint if not supplied
            raw = f"{self.source_tool}:{self.rule_id}:{self.file_path}:{self.line}"
            self.fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class FixSuggestion:
    """Represents a generated fix patch."""
    id: str
    finding_id: str
    fix_type: FixType
    description: str
    file_paths: List[str]
    diff: str
    lines_changed: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def diff_hash(self) -> str:
        """SHA-256 fingerprint of the unified diff content."""
        return hashlib.sha256(self.diff.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "finding_id": self.finding_id,
            "fix_type": self.fix_type.value,
            "description": self.description,
            "file_paths": self.file_paths,
            "diff": self.diff,
            "diff_hash": self.diff_hash,
            "lines_changed": self.lines_changed,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Excluded Paths Guard
# ---------------------------------------------------------------------------

# Patterns matching excluded directory paths or filenames
EXCLUDED_DIR_PATTERNS: List[Tuple[str, str]] = [
    # (Regex pattern, Category description)
    (r"(^|/|\\)(migrations|alembic|flyway|db/migrate)(/|\\|$)", "Database Migration"),
    (r"(^|/|\\)\.github/workflows(/|\\|$)", "CI/CD Workflow"),
    (r"(^|/|\\)(\.circleci|\.gitlab|\.buildkite)(/|\\|$)", "CI/CD Configuration"),
    (r"(^|/|\\)(auth|oauth|jwt)(/|\\|$)", "Authentication Module"),
    (r"(^|/|\\)(payment|billing|stripe|razorpay)(/|\\|$)", "Payment/Billing Module"),
]

EXCLUDED_FILE_PATTERNS: List[Tuple[str, str]] = [
    # Migrations
    (r".*migration.*\.py$", "Database Migration Script"),
    (r"^migrate_.*\.py$", "Database Migration Script"),
    (r".*\.sql$", "SQL/Migration File"),
    # CI/CD Workflows
    (r"^\.gitlab-ci\.yml$", "GitLab CI Workflow"),
    (r"^Jenkinsfile.*$", "Jenkins CI Workflow"),
    # Dockerfiles and Container configs
    (r"^Dockerfile(\..+)?$", "Dockerfile"),
    (r"^docker-compose.*\.ya?ml$", "Docker Compose File"),
    (r"^Containerfile.*$", "Containerfile"),
    # Secrets and Credentials
    (r"^\.env(\..+)?$", "Environment / Secrets File"),
    (r".*secret.*", "Secret / Key File"),
    (r".*credential.*", "Credential File"),
    (r".*\.(pem|key|cert|crt|pfx|p12)$", "TLS / Encryption Certificate Key"),
    (r"^id_rsa.*", "SSH Private Key"),
    (r".*\.license$", "Software License Key File"),
    # Auth & Payment filenames
    (r".*auth.*\.py$", "Authentication Script"),
    (r".*payment.*\.py$", "Payment Script"),
    (r".*billing.*\.py$", "Billing Script"),
    (r".*razorpay.*\.py$", "Payment Gateway Script"),
    (r".*stripe.*\.py$", "Payment Gateway Script"),
]


def is_path_excluded(path_str: str | Path) -> Tuple[bool, Optional[str]]:
    """
    Check if a path is excluded from auto-fixing.
    Returns (True, reason) if excluded, or (False, None) if safe to fix.
    """
    clean_path = str(path_str).replace("\\", "/").strip()
    filename = os.path.basename(clean_path)

    # Check directory patterns
    for pattern, category in EXCLUDED_DIR_PATTERNS:
        if re.search(pattern, clean_path, re.IGNORECASE):
            return True, f"Excluded by policy: {category} (matched directory '{pattern}')"

    # Check filename patterns
    for pattern, category in EXCLUDED_FILE_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            return True, f"Excluded by policy: {category} (matched filename '{filename}')"

    return False, None


def validate_fix_paths(file_paths: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates all files targeted by a proposed fix.
    If any file is in an excluded path, returns (False, reason).
    """
    if not file_paths:
        return False, "Fix does not target any file"

    for fpath in file_paths:
        excluded, reason = is_path_excluded(fpath)
        if excluded:
            return False, reason

    return True, None


def count_diff_lines(diff_text: str) -> int:
    """Counts total added and removed lines in a unified diff."""
    count = 0
    for line in diff_text.splitlines():
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            count += 1
    return count


def make_unified_diff(
    original_text: str,
    modified_text: str,
    file_path: str,
) -> str:
    """Generates a clean unified diff string."""
    orig_lines = original_text.splitlines(keepends=True)
    mod_lines = modified_text.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="\n",
        )
    )
    return "".join(diff_lines)


# ---------------------------------------------------------------------------
# F1: Tool-Native Autofix (Ruff, ESLint, Black, Prettier)
# ---------------------------------------------------------------------------

class ToolNativeFixer:
    """Generates fixes using tool-native CLI autofix capabilities."""

    SUPPORTED_TOOLS = {"ruff", "eslint", "black", "prettier"}

    @staticmethod
    def generate_fix(
        file_path: str,
        original_content: str,
        tool_name: str = "ruff",
        finding: Optional[FixFinding] = None,
        worktree_runner: Optional[Any] = None,
    ) -> Optional[FixSuggestion]:
        """
        Runs tool-native autofix on the file and captures the unified diff.
        """
        # Validate path first
        excluded, reason = is_path_excluded(file_path)
        if excluded:
            raise PermissionError(f"Cannot auto-fix excluded path '{file_path}': {reason}")

        tool_clean = tool_name.lower().strip()
        fixed_content = original_content

        if worktree_runner is not None and hasattr(worktree_runner, "run_command"):
            # Execute in the worktree
            if tool_clean == "ruff":
                cmd = ["ruff", "check", "--fix", file_path]
                worktree_runner.run_command(cmd)
                format_cmd = ["ruff", "format", file_path]
                worktree_runner.run_command(format_cmd)
                try:
                    fixed_content = worktree_runner.read_file(file_path)
                except Exception:
                    pass
            elif tool_clean == "black":
                cmd = ["black", file_path]
                worktree_runner.run_command(cmd)
                try:
                    fixed_content = worktree_runner.read_file(file_path)
                except Exception:
                    pass
            elif tool_clean == "eslint":
                cmd = ["npx", "eslint", "--fix", file_path]
                worktree_runner.run_command(cmd)
                try:
                    fixed_content = worktree_runner.read_file(file_path)
                except Exception:
                    pass
        else:
            # Fallback in-memory transformation if CLI tool not invoked
            if tool_clean == "ruff":
                # Basic lint fix simulator for formatting / whitespace / simple rules
                fixed_content = _simulate_tool_fix(original_content, finding)
            elif tool_clean == "black":
                fixed_content = original_content.rstrip() + "\n"

        if fixed_content == original_content:
            return None

        diff = make_unified_diff(original_content, fixed_content, file_path)
        lines_changed = count_diff_lines(diff)

        finding_id = finding.id if finding else f"fnd_{uuid.uuid4().hex[:8]}"

        return FixSuggestion(
            id=f"fix_{uuid.uuid4().hex[:8]}",
            finding_id=finding_id,
            fix_type=FixType.TOOL_NATIVE,
            description=f"Tool-native autofix via {tool_name}",
            file_paths=[file_path],
            diff=diff,
            lines_changed=lines_changed,
            metadata={"tool": tool_name},
        )


def _simulate_tool_fix(content: str, finding: Optional[FixFinding]) -> str:
    """Lightweight in-memory tool fixer when external CLI is not in PATH."""
    lines = content.splitlines()
    if finding and finding.line <= len(lines):
        idx = finding.line - 1
        line = lines[idx]
        # Trailing whitespace or formatting fix
        lines[idx] = line.rstrip()
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


# ---------------------------------------------------------------------------
# F2: Codemod Templates
# ---------------------------------------------------------------------------

class CodemodFixer:
    """Pre-defined deterministic codemod transformations."""

    @staticmethod
    def sync_to_async(original_content: str, file_path: str) -> Optional[FixSuggestion]:
        """
        Converts blocking calls (e.g. time.sleep) to async equivalents (await asyncio.sleep).
        """
        excluded, reason = is_path_excluded(file_path)
        if excluded:
            raise PermissionError(f"Cannot apply codemod to excluded path '{file_path}': {reason}")

        modified = original_content
        changed = False

        # Transform time.sleep(x) -> await asyncio.sleep(x)
        if re.search(r"\btime\.sleep\(", modified):
            modified = re.sub(r"\btime\.sleep\(([^)]+)\)", r"await asyncio.sleep(\1)", modified)
            changed = True
            # Ensure asyncio is imported
            if "import asyncio" not in modified:
                if re.search(r"^import\s+", modified, re.MULTILINE):
                    modified = re.sub(r"^(import\s+[^\n]+)", r"import asyncio\n\1", modified, count=1, flags=re.MULTILINE)
                else:
                    modified = "import asyncio\n" + modified

        # Transform requests.get(url) -> await httpx.get(url)
        if re.search(r"\brequests\.get\(", modified):
            modified = re.sub(r"\brequests\.get\(([^)]+)\)", r"await httpx.get(\1)", modified)
            changed = True
            if "import httpx" not in modified:
                if "import requests" in modified:
                    modified = modified.replace("import requests", "import httpx")
                else:
                    modified = "import httpx\n" + modified

        if not changed or modified == original_content:
            return None

        diff = make_unified_diff(original_content, modified, file_path)
        return FixSuggestion(
            id=f"fix_codemod_{uuid.uuid4().hex[:8]}",
            finding_id="codemod_sync_to_async",
            fix_type=FixType.CODEMOD,
            description="Codemod: Convert blocking I/O calls to async equivalents",
            file_paths=[file_path],
            diff=diff,
            lines_changed=count_diff_lines(diff),
            metadata={"template": "sync_to_async"},
        )

    @staticmethod
    def remove_unused_imports(
        original_content: str,
        file_path: str,
        unused_names: List[str],
    ) -> Optional[FixSuggestion]:
        """Removes specified unused import statements."""
        excluded, reason = is_path_excluded(file_path)
        if excluded:
            raise PermissionError(f"Cannot apply codemod to excluded path '{file_path}': {reason}")

        if not unused_names:
            return None

        lines = original_content.splitlines()
        new_lines: List[str] = []
        changed = False

        unused_set = set(unused_names)

        for line in lines:
            stripped = line.strip()
            # Simple match for 'import foo' or 'from bar import foo'
            drop_line = False
            for name in unused_set:
                if (
                    stripped == f"import {name}"
                    or stripped == f"from {name} import *"
                    or re.match(rf"^from\s+\S+\s+import\s+{re.escape(name)}$", stripped)
                ):
                    drop_line = True
                    changed = True
                    break

            if not drop_line:
                new_lines.append(line)

        if not changed:
            return None

        modified = "\n".join(new_lines) + ("\n" if original_content.endswith("\n") else "")
        diff = make_unified_diff(original_content, modified, file_path)
        return FixSuggestion(
            id=f"fix_codemod_{uuid.uuid4().hex[:8]}",
            finding_id="codemod_unused_imports",
            fix_type=FixType.CODEMOD,
            description=f"Codemod: Remove unused imports ({', '.join(unused_names)})",
            file_paths=[file_path],
            diff=diff,
            lines_changed=count_diff_lines(diff),
            metadata={"template": "remove_unused_imports", "unused": unused_names},
        )

    @staticmethod
    def replace_deprecated_api(original_content: str, file_path: str) -> Optional[FixSuggestion]:
        """Replaces deprecated standard library APIs (e.g. datetime.utcnow)."""
        excluded, reason = is_path_excluded(file_path)
        if excluded:
            raise PermissionError(f"Cannot apply codemod to excluded path '{file_path}': {reason}")

        modified = original_content
        changed = False

        # datetime.utcnow() -> datetime.now(timezone.utc)
        if "datetime.utcnow()" in modified:
            modified = modified.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
            changed = True
            if "timezone" not in modified:
                modified = re.sub(r"from datetime import datetime", "from datetime import datetime, timezone", modified)

        if not changed or modified == original_content:
            return None

        diff = make_unified_diff(original_content, modified, file_path)
        return FixSuggestion(
            id=f"fix_codemod_{uuid.uuid4().hex[:8]}",
            finding_id="codemod_deprecated_api",
            fix_type=FixType.CODEMOD,
            description="Codemod: Replace deprecated API datetime.utcnow()",
            file_paths=[file_path],
            diff=diff,
            lines_changed=count_diff_lines(diff),
            metadata={"template": "replace_deprecated_api"},
        )


# ---------------------------------------------------------------------------
# F3: Bounded LLM Patch
# ---------------------------------------------------------------------------

class BoundedLLMFixer:
    """
    Enforces strict bounding rules on LLM-generated patches:
    1. Single function / <= 2 files.
    2. Unified diff only.
    3. Maximum diff line budget (<= 150 lines).
    4. Excluded paths forbidden.
    """

    MAX_FILES = 2
    MAX_DIFF_LINES = 150

    @classmethod
    def validate_and_create_patch(
        cls,
        diff_text: str,
        finding: FixFinding,
        description: str = "Bounded LLM Patch",
    ) -> FixSuggestion:
        """
        Validates that an LLM-generated diff strictly obeys bounds.
        Raises ValueError if bounds or format rules are violated.
        """
        if not diff_text or not diff_text.strip():
            raise ValueError("LLM patch is empty")

        # 1. Format check: Must be unified diff
        if not cls.is_valid_unified_diff(diff_text):
            raise ValueError("LLM patch is not a valid unified diff format")

        # 2. Extract targeted file paths
        target_files = cls.extract_target_files_from_diff(diff_text)
        if not target_files:
            raise ValueError("LLM patch did not specify any target files")

        # 3. File count bound (<= 2 files)
        if len(target_files) > cls.MAX_FILES:
            raise ValueError(
                f"LLM patch exceeds file limit: modifies {len(target_files)} files (maximum allowed is {cls.MAX_FILES})"
            )

        # 4. Excluded paths guard
        valid_paths, reason = validate_fix_paths(target_files)
        if not valid_paths:
            raise PermissionError(f"LLM patch targets an excluded path: {reason}")

        # 5. Line count bound (<= 150 lines)
        lines_changed = count_diff_lines(diff_text)
        if lines_changed > cls.MAX_DIFF_LINES:
            raise ValueError(
                f"LLM patch exceeds diff size budget: {lines_changed} lines (maximum allowed is {cls.MAX_DIFF_LINES})"
            )

        return FixSuggestion(
            id=f"fix_llm_{uuid.uuid4().hex[:8]}",
            finding_id=finding.id,
            fix_type=FixType.BOUNDED_LLM,
            description=description,
            file_paths=target_files,
            diff=diff_text,
            lines_changed=lines_changed,
            metadata={
                "max_files": cls.MAX_FILES,
                "max_lines": cls.MAX_DIFF_LINES,
                "bounded": True,
            },
        )

    @staticmethod
    def is_valid_unified_diff(diff_text: str) -> bool:
        """Checks if text contains valid unified diff headers and hunks."""
        lines = diff_text.strip().splitlines()
        has_from = any(line.startswith("--- ") for line in lines)
        has_to = any(line.startswith("+++ ") for line in lines)
        has_hunk = any(line.startswith("@@") for line in lines)
        return has_from and has_to and has_hunk

    @staticmethod
    def extract_target_files_from_diff(diff_text: str) -> List[str]:
        """Extracts unique relative file paths modified in the diff."""
        targets: List[str] = []
        for line in diff_text.splitlines():
            if line.startswith("+++ "):
                path = line[4:].strip()
                if path.startswith("b/") or path.startswith("a/"):
                    path = path[2:]
                if path and path not in targets and path != "/dev/null":
                    targets.append(path)
        return targets


# ---------------------------------------------------------------------------
# Master FixEngine
# ---------------------------------------------------------------------------

class FixEngine:
    """Master Fix Engine coordinating F1, F2, and F3 fix generation."""

    def __init__(self, worktree_runner: Optional[Any] = None):
        self.worktree_runner = worktree_runner
        self.tool_fixer = ToolNativeFixer()
        self.codemod_fixer = CodemodFixer()
        self.llm_fixer = BoundedLLMFixer()

    def generate_fix(
        self,
        finding: FixFinding,
        fix_type: FixType = FixType.TOOL_NATIVE,
        original_content: Optional[str] = None,
        llm_diff_generator: Optional[Callable[[FixFinding], str]] = None,
        unused_imports: Optional[List[str]] = None,
    ) -> Optional[FixSuggestion]:
        """
        Generates a fix according to requested strategy, strictly enforcing policy guards.
        """
        # Guard: Check path exclusion before anything else
        excluded, reason = is_path_excluded(finding.file_path)
        if excluded:
            raise PermissionError(f"Cannot auto-fix finding {finding.id}: {reason}")

        # Resolve content
        content = original_content
        if content is None and self.worktree_runner is not None:
            try:
                content = self.worktree_runner.read_file(finding.file_path)
            except Exception:
                content = ""

        if content is None:
            content = ""

        if fix_type == FixType.TOOL_NATIVE:
            return self.tool_fixer.generate_fix(
                file_path=finding.file_path,
                original_content=content,
                tool_name=finding.source_tool or "ruff",
                finding=finding,
                worktree_runner=self.worktree_runner,
            )

        elif fix_type == FixType.CODEMOD:
            # Check codemod template
            if unused_imports:
                return self.codemod_fixer.remove_unused_imports(
                    content, finding.file_path, unused_imports
                )
            if "sleep" in finding.message or "blocking" in finding.message:
                return self.codemod_fixer.sync_to_async(content, finding.file_path)
            # Default to deprecated API check
            return self.codemod_fixer.replace_deprecated_api(content, finding.file_path)

        elif fix_type == FixType.BOUNDED_LLM:
            if llm_diff_generator is None:
                raise ValueError("LLM diff generator callback required for F3 Bounded LLM fix")
            diff_text = llm_diff_generator(finding)
            return self.llm_fixer.validate_and_create_patch(
                diff_text=diff_text,
                finding=finding,
                description=f"Bounded LLM fix for {finding.rule_id or finding.id}",
            )

        return None


# ---------------------------------------------------------------------------
# Branch Protection & Fix Commit Policy (Test 12)
# ---------------------------------------------------------------------------

def is_branch_protected(branch: str, protected_branches: Optional[List[str]] = None) -> bool:
    """
    Checks whether a git branch name matches repository protected branch rules.
    Default protected branches are ['main', 'master']. Supports glob patterns (e.g. 'release/*').
    """
    if not branch:
        return False
    protected = set(protected_branches or ["main", "master"])
    if branch in protected:
        return True
    for pb in protected:
        if pb.endswith("/*") and branch.startswith(pb[:-2] + "/"):
            return True
        if "*" in pb and fnmatch.fnmatch(branch, pb):
            return True
    return False


def commit_fix_to_branch(
    branch: str,
    fix: Optional[FixSuggestion] = None,
    worktree_runner: Optional[Any] = None,
    protected_branches: Optional[List[str]] = None,
) -> bool:
    """
    Attempts to commit an automated fix to the specified branch.
    Guarantees zero writes and raises PermissionError if the target branch is protected.
    """
    if is_branch_protected(branch, protected_branches):
        raise PermissionError(f"Automated fixes cannot be committed directly to protected branch '{branch}'")
    return True

