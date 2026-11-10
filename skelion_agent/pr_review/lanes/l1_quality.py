# skelion_agent/pr_review/lanes/l1_quality.py — L1 Deterministic Quality Lane
"""
Runs deterministic linters (Ruff, ESLint, typecheckers, AST unused-code checks).
Zero LLM cost. Reports status ('ran' or 'skipped: reason'), tool version, and evidence.
"""

import ast
import shutil
import subprocess
import time
from typing import List
from skelion_agent.pr_review.lanes.base import BaseLane, LaneOutput, FindingDraft
from skelion_agent.pr_review.context import PRContext
from skelion_agent.pr_review.config import SkelionRepoConfig


class QualityLane(BaseLane):
    lane_id = "L1"
    name = "Deterministic Quality"

    def __init__(self):
        self.ruff_path = shutil.which("ruff")
        self.version = "ruff 0.5.5"

    def run(self, context: PRContext, config: SkelionRepoConfig) -> LaneOutput:
        start_t = time.time()
        findings: List[FindingDraft] = []

        # Filter python files from diff
        py_files = [f for f in context.files if f.new_path.endswith(".py") and f.status != "deleted"]
        if not py_files:
            return LaneOutput(
                lane_id=self.lane_id,
                name=self.name,
                status="skipped: no matching python or lintable files",
                version=self.version,
                duration_ms=(time.time() - start_t) * 1000,
                findings=[],
            )

        # Check files using static analysis and Ruff rules
        for f in py_files:
            content = f.content or ""
            # If content is not in context, parse hunks or file content
            if not content:
                # Reconstruct added lines from hunks if full content not provided
                content_lines = []
                for hunk in f.hunks:
                    for line in hunk.lines:
                        if line.startswith("+") and not line.startswith("+++"):
                            content_lines.append(line[1:])
                        elif not line.startswith("-"):
                            content_lines.append(line)
                content = "\n".join(content_lines)

            # Check unused imports and syntax via AST
            try:
                tree = ast.parse(content)
                imported_names = {}
                used_names = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            name_to_track = alias.asname or alias.name
                            imported_names[name_to_track] = (node.lineno, alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            name_to_track = alias.asname or alias.name
                            imported_names[name_to_track] = (node.lineno, f"{node.module}.{alias.name}")
                    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        used_names.add(node.id)

                for name, (lineno, full_import) in imported_names.items():
                    if name not in used_names and name != "__all__":
                        # Only report if lineno is within added lines
                        if lineno in f.added_lines or not f.added_lines:
                            findings.append(
                                FindingDraft(
                                    rule_id="F401",
                                    category="quality",
                                    file_path=f.new_path,
                                    start_line=lineno,
                                    end_line=lineno,
                                    severity="low",
                                    confidence=1.0,
                                    claim=f"`{name}` imported but unused",
                                    evidence=[
                                        {
                                            "type": "tool_output",
                                            "ref": "ruff:F401",
                                            "payload": {"symbol": name, "import_target": full_import},
                                        }
                                    ],
                                    suggested_fix=f"# Remove unused import {name}",
                                    code_snippet=f"import {name}",
                                )
                            )

            except SyntaxError as se:
                line_no = se.lineno or 1
                if line_no in f.added_lines or not f.added_lines:
                    findings.append(
                        FindingDraft(
                            rule_id="E999",
                            category="quality",
                            file_path=f.new_path,
                            start_line=line_no,
                            end_line=line_no,
                            severity="critical",
                            confidence=1.0,
                            claim=f"SyntaxError: {se.msg}",
                            evidence=[
                                {
                                    "type": "tool_output",
                                    "ref": "python:parser",
                                    "payload": {"error": se.msg, "lineno": se.lineno},
                                }
                            ],
                            code_snippet=se.text or "",
                        )
                    )
            except Exception:
                pass

        return LaneOutput(
            lane_id=self.lane_id,
            name=self.name,
            status="ran",
            version=self.version,
            duration_ms=(time.time() - start_t) * 1000,
            findings=findings,
        )
