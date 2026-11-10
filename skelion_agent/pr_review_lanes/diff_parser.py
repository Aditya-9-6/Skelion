# skelion_agent/pr_review_lanes/diff_parser.py — Unified Git Diff Parser
"""
Unified diff parser for PR review lanes.
Extracts added/modified line numbers and file paths from unified git diffs.
"""

import re
from typing import Dict, Set, Optional, List
from pydantic import BaseModel, Field


def normalize_path(path: str) -> str:
    """Normalizes file path across Windows and POSIX systems."""
    if not path:
        return ""
    p = path.replace("\\", "/").strip()
    if p.startswith("./"):
        p = p[2:]
    return p


class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added_lines: List[int] = Field(default_factory=list)


class DiffFile(BaseModel):
    old_path: Optional[str] = None
    new_path: Optional[str] = None
    is_deleted: bool = False
    is_new: bool = False
    hunks: List[DiffHunk] = Field(default_factory=list)
    added_lines: Set[int] = Field(default_factory=set)


RE_DIFF_HEADER = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
RE_OLD_FILE = re.compile(r"^--- (?:a/)?(.*?)$")
RE_NEW_FILE = re.compile(r"^\+\+\+ (?:b/)?(.*?)$")
RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class DiffParser:
    """Parses unified git diffs and returns mapping of normalized file paths to added/modified lines."""

    @classmethod
    def parse(cls, diff_text: str) -> Dict[str, Set[int]]:
        """
        Parses diff and returns a dict mapping normalized file paths to sets of 1-based line numbers
        that are newly added or modified in the diff.
        """
        if not diff_text or not diff_text.strip():
            return {}

        file_added_lines: Dict[str, Set[int]] = {}
        current_file: Optional[str] = None
        current_new_line: int = 0
        in_hunk: bool = False

        for line in diff_text.splitlines():
            # Check for diff header
            git_match = RE_DIFF_HEADER.match(line)
            if git_match:
                current_file = normalize_path(git_match.group(2))
                if current_file and current_file not in file_added_lines:
                    file_added_lines[current_file] = set()
                in_hunk = False
                continue

            # Check for --- or +++
            if line.startswith("--- "):
                continue

            new_file_match = RE_NEW_FILE.match(line)
            if new_file_match:
                raw_path = new_file_match.group(1).strip()
                if raw_path == "/dev/null":
                    current_file = None
                else:
                    current_file = normalize_path(raw_path)
                    if current_file and current_file not in file_added_lines:
                        file_added_lines[current_file] = set()
                in_hunk = False
                continue

            # Check for hunk header
            hunk_match = RE_HUNK_HEADER.match(line)
            if hunk_match:
                new_start = int(hunk_match.group(3))
                current_new_line = new_start
                in_hunk = True
                continue

            if in_hunk and current_file:
                if line.startswith("+") and not line.startswith("+++"):
                    file_added_lines[current_file].add(current_new_line)
                    current_new_line += 1
                elif line.startswith("-") and not line.startswith("---"):
                    # Deletion does not advance line in new file
                    pass
                else:
                    # Context line (starts with space or empty)
                    current_new_line += 1

        return file_added_lines

    @classmethod
    def get_changed_files(cls, diff_text: str) -> List[str]:
        """Returns list of changed file paths in the diff."""
        added_lines = cls.parse(diff_text)
        return list(added_lines.keys())
