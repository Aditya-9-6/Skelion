# skelion_agent/pr_review/context.py — PR Context Builder and Diff Parser
"""
Extracts diff details, added/changed line sets per file, enclosing symbols,
and prepares safe untrusted-data wrapped context with token budgeting.
"""

import ast
import re
from typing import Dict, List, Set, Any, Optional
from pydantic import BaseModel


class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]


class DiffFile(BaseModel):
    old_path: Optional[str]
    new_path: str
    status: str  # added, modified, deleted, renamed
    hunks: List[DiffHunk]
    added_lines: List[int]  # Line numbers of added/modified lines in new file
    deleted_lines: List[int]
    content: Optional[str] = None  # Full new file content if available


class PRContext(BaseModel):
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    title: str
    description: str
    is_fork: bool = False
    files: List[DiffFile] = []
    codeowners: Dict[str, List[str]] = {}
    total_added: int = 0
    total_deleted: int = 0


def parse_unified_diff(diff_text: str) -> List[DiffFile]:
    """Parse unified git diff into DiffFile objects with precise added_lines sets."""
    files: List[DiffFile] = []
    if not diff_text or not diff_text.strip():
        return files

    file_chunks = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    for chunk in file_chunks:
        if not chunk.strip():
            continue

        lines = chunk.splitlines()
        old_path: Optional[str] = None
        new_path: Optional[str] = None
        status = "modified"

        # Read diff headers
        for line in lines[:10]:
            if line.startswith("--- a/"):
                old_path = line[6:]
            elif line.startswith("--- /dev/null"):
                old_path = None
                status = "added"
            elif line.startswith("+++ b/"):
                new_path = line[6:]
            elif line.startswith("+++ /dev/null"):
                new_path = old_path or "deleted_file"
                status = "deleted"
            elif line.startswith("diff --git a/"):
                parts = line.split(" b/")
                if len(parts) == 2:
                    old_path = parts[0].replace("diff --git a/", "")
                    new_path = parts[1]

        if not new_path:
            continue

        hunks: List[DiffHunk] = []
        added_lines: List[int] = []
        deleted_lines: List[int] = []

        current_hunk_lines: List[str] = []
        current_old_start = 0
        current_old_count = 0
        current_new_start = 0
        current_new_count = 0
        current_new_line_ptr = 0

        hunk_header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

        for line in lines:
            hunk_match = hunk_header_re.match(line)
            if hunk_match:
                if current_hunk_lines:
                    hunks.append(
                        DiffHunk(
                            old_start=current_old_start,
                            old_count=current_old_count,
                            new_start=current_new_start,
                            new_count=current_new_count,
                            lines=current_hunk_lines,
                        )
                    )
                    current_hunk_lines = []

                current_old_start = int(hunk_match.group(1))
                current_old_count = int(hunk_match.group(2) or 1)
                current_new_start = int(hunk_match.group(3))
                current_new_count = int(hunk_match.group(4) or 1)
                current_new_line_ptr = current_new_start
                current_hunk_lines.append(line)
            elif current_hunk_lines:
                current_hunk_lines.append(line)
                if line.startswith("+") and not line.startswith("+++"):
                    added_lines.append(current_new_line_ptr)
                    current_new_line_ptr += 1
                elif line.startswith("-") and not line.startswith("---"):
                    pass
                else:
                    current_new_line_ptr += 1

        if current_hunk_lines:
            hunks.append(
                DiffHunk(
                    old_start=current_old_start,
                    old_count=current_old_count,
                    new_start=current_new_start,
                    new_count=current_new_count,
                    lines=current_hunk_lines,
                )
            )

        files.append(
            DiffFile(
                old_path=old_path,
                new_path=new_path,
                status=status,
                hunks=hunks,
                added_lines=added_lines,
                deleted_lines=deleted_lines,
            )
        )

    return files


def extract_symbols_for_lines(source_code: str, target_lines: Set[int]) -> Dict[int, str]:
    """
    Given a Python source file, maps each line in target_lines to its enclosing function or class.
    Falls back gracefully if syntax is invalid or not Python.
    """
    line_to_symbol: Dict[int, str] = {}
    if not source_code:
        return line_to_symbol

    try:
        tree = ast.parse(source_code)
    except Exception:
        # Fallback regex for non-python or unparseable
        for line_no in target_lines:
            line_to_symbol[line_no] = "<module>"
        return line_to_symbol

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start + 20)
            name = node.name
            for line_no in target_lines:
                if start <= line_no <= end:
                    line_to_symbol[line_no] = name

    # Default remaining
    for line_no in target_lines:
        if line_no not in line_to_symbol:
            line_to_symbol[line_no] = "<module>"

    return line_to_symbol


def wrap_untrusted_data(label: str, content: str) -> str:
    """Wraps untrusted data with tamper-resistant boundary tags to protect prompt parsing."""
    return f"<<<UNTRUSTED_DATA_START:{label}>>>\n{content}\n<<<UNTRUSTED_DATA_END:{label}>>>"
