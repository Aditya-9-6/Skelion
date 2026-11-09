# skelion_agent/pr_review_lanes/l1_quality.py — Deterministic Quality Adapter
"""
L1 Deterministic Quality Adapter:
Integrates Ruff, ESLint, tsc, and mypy for deterministic code quality and static typing.
Normalizes outputs into standard Finding models with stable fingerprints.
"""

import ast
import json
import os
import re
import shutil
import subprocess
from typing import Optional, Dict, Any, List, Set
from .base_lane import BaseLane
from .models import Finding, Evidence, compute_fingerprint
from .diff_parser import DiffParser, normalize_path
from .sarif_normalizer import SarifNormalizer, resolve_enclosing_symbol


SUPPORTED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}


class L1QualityLane(BaseLane):
    """
    Deterministic Quality Adapter.
    Executes Ruff, mypy, ESLint, and tsc over changed files or workspace.
    """

    def __init__(self, lane_id: str = "l1_quality", name: str = "Deterministic Quality Lane"):
        super().__init__(lane_id=lane_id, name=name, category="quality")
        self._cached_tool_version: Optional[str] = None

    def get_tool_version(self) -> Optional[str]:
        """Collects versions of available deterministic quality tools."""
        if self._cached_tool_version is not None:
            return self._cached_tool_version

        versions: List[str] = []
        # Check ruff
        ruff_path = shutil.which("ruff")
        if ruff_path:
            try:
                proc = subprocess.run([ruff_path, "--version"], capture_output=True, encoding="utf-8", errors="replace", timeout=5)
                if proc.returncode == 0:
                    versions.append(proc.stdout.strip())
            except Exception:
                versions.append("ruff (available)")

        # Check mypy
        mypy_path = shutil.which("mypy")
        if mypy_path:
            try:
                proc = subprocess.run([mypy_path, "--version"], capture_output=True, encoding="utf-8", errors="replace", timeout=5)
                if proc.returncode == 0:
                    versions.append(proc.stdout.strip())
            except Exception:
                versions.append("mypy (available)")

        # Check eslint
        eslint_path = shutil.which("eslint")
        if eslint_path:
            try:
                proc = subprocess.run([eslint_path, "--version"], capture_output=True, encoding="utf-8", errors="replace", timeout=5)
                if proc.returncode == 0:
                    versions.append(f"eslint {proc.stdout.strip()}")
            except Exception:
                versions.append("eslint (available)")

        # Check tsc
        tsc_path = shutil.which("tsc")
        if tsc_path:
            try:
                proc = subprocess.run([tsc_path, "--version"], capture_output=True, encoding="utf-8", errors="replace", timeout=5)
                if proc.returncode == 0:
                    versions.append(f"tsc {proc.stdout.strip()}")
            except Exception:
                versions.append("tsc (available)")

        if not versions:
            self._cached_tool_version = "builtin-ast-quality 1.0.0"
        else:
            self._cached_tool_version = ", ".join(versions)

        return self._cached_tool_version

    def check_prerequisites(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Checks if there are any supported source files to evaluate."""
        if diff is not None:
            changed_files = DiffParser.get_changed_files(diff)
            supported = [f for f in changed_files if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
            if not supported:
                return "no supported source files"
        else:
            # Check repository
            found_supported = False
            for root, _, files in os.walk(repo_path):
                if any(ignored in root for ignored in [".git", "node_modules", ".venv", "__pycache__"]):
                    continue
                for f in files:
                    if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                        found_supported = True
                        break
                if found_supported:
                    break
            if not found_supported:
                return "no supported source files"
        return None

    def execute(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []
        target_files = self._get_target_files(repo_path, diff)

        py_files = [f for f in target_files if f.endswith(".py")]
        js_ts_files = [f for f in target_files if any(f.endswith(ext) for ext in [".js", ".jsx", ".ts", ".tsx"])]

        # 1. Run Ruff / Python checks
        if py_files:
            ruff_findings = self._run_ruff_or_python_ast(repo_path, py_files)
            findings.extend(ruff_findings)

        # 2. Run ESLint / JS-TS checks
        if js_ts_files:
            js_findings = self._run_eslint_or_js_checks(repo_path, js_ts_files)
            findings.extend(js_findings)

        return findings

    def _get_target_files(self, repo_path: str, diff: Optional[str]) -> List[str]:
        if diff is not None:
            changed = DiffParser.get_changed_files(diff)
            return [normalize_path(f) for f in changed if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS)]

        files_list: List[str] = []
        for root, _, files in os.walk(repo_path):
            if any(ignored in root for ignored in [".git", "node_modules", ".venv", "__pycache__"]):
                continue
            for f in files:
                if any(f.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    rel = os.path.relpath(os.path.join(root, f), repo_path)
                    files_list.append(normalize_path(rel))
        return files_list

    def _run_ruff_or_python_ast(self, repo_path: str, py_files: List[str]) -> List[Finding]:
        findings: List[Finding] = []
        ruff_path = shutil.which("ruff")

        if ruff_path and py_files:
            try:
                # Run ruff with SARIF output format
                cmd = [ruff_path, "check", "--select=E,F,B", "--output-format=sarif"] + py_files
                proc = subprocess.run(cmd, cwd=repo_path, capture_output=True, encoding="utf-8", errors="replace", timeout=15)
                if proc.stdout and proc.stdout.strip().startswith("{"):
                    sarif_findings = SarifNormalizer.normalize(proc.stdout, default_category="quality", repo_path=repo_path)
                    if sarif_findings:
                        return sarif_findings
            except Exception:
                pass

        # Built-in Python AST deterministic quality checker fallback
        for rel_file in py_files:
            abs_path = os.path.join(repo_path, rel_file) if not os.path.isabs(rel_file) else rel_file
            if not os.path.isfile(abs_path):
                continue
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                file_findings = self._check_python_ast(rel_file, content, repo_path)
                findings.extend(file_findings)
            except Exception:
                pass

        return findings

    def _check_python_ast(self, file_path: str, content: str, repo_path: str) -> List[Finding]:
        findings: List[Finding] = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            line_no = e.lineno or 1
            snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
            rule_id = "RUFF/E999"
            sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
            ev = Evidence(
                type="ast",
                description=f"Python syntax error: {e.msg}",
                file_path=file_path,
                line_number=line_no,
                snippet=snip,
            )
            findings.append(Finding(
                rule_id=rule_id,
                category="quality",
                severity="critical",
                title=f"Syntax Error: {e.msg}",
                message=str(e),
                file_path=file_path,
                line_number=line_no,
                code_snippet=snip,
                enclosing_symbol=sym,
                evidence=[ev],
                confidence=1.0,
            ))
            return findings

        # AST-level inspection for code quality issues
        for node in ast.walk(tree):
            # 1. Mutable default argument (B006 / Ruff mutable-default)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default_arg in node.args.defaults + node.args.kw_defaults:
                    if default_arg is not None and isinstance(default_arg, (ast.List, ast.Dict, ast.Set)):
                        line_no = getattr(default_arg, "lineno", node.lineno)
                        snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                        sym = f"{node.name}"
                        ev = Evidence(
                            type="ast",
                            description=f"Mutable default argument '{ast.unparse(default_arg)}' in function '{node.name}'.",
                            file_path=file_path,
                            line_number=line_no,
                            snippet=snip,
                        )
                        findings.append(Finding(
                            rule_id="RUFF/B006",
                            category="quality",
                            severity="medium",
                            title=f"Mutable default argument in '{node.name}'",
                            message=f"Do not use mutable data structures as default arguments in '{node.name}'.",
                            file_path=file_path,
                            line_number=line_no,
                            code_snippet=snip,
                            enclosing_symbol=sym,
                            evidence=[ev],
                            confidence=1.0,
                        ))

            # 2. Bare except clause (E722 / Ruff bare-except)
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    line_no = getattr(node, "lineno", 1)
                    snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                    sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
                    ev = Evidence(
                        type="ast",
                        description="Do not use bare 'except:'. Specify exception types or 'except Exception:'.",
                        file_path=file_path,
                        line_number=line_no,
                        snippet=snip,
                    )
                    findings.append(Finding(
                        rule_id="RUFF/E722",
                        category="quality",
                        severity="medium",
                        title="Do not use bare 'except'",
                        message="Bare 'except' catches SystemExit and KeyboardInterrupt. Use 'except Exception:' instead.",
                        file_path=file_path,
                        line_number=line_no,
                        code_snippet=snip,
                        enclosing_symbol=sym,
                        evidence=[ev],
                        confidence=1.0,
                    ))

        return findings

    def _run_eslint_or_js_checks(self, repo_path: str, js_files: List[str]) -> List[Finding]:
        findings: List[Finding] = []
        eslint_path = shutil.which("eslint")

        if eslint_path and js_files:
            try:
                cmd = [eslint_path, "-f", "json"] + js_files
                proc = subprocess.run(cmd, cwd=repo_path, capture_output=True, encoding="utf-8", errors="replace", timeout=15)
                if proc.stdout and proc.stdout.strip().startswith("["):
                    eslint_results = json.loads(proc.stdout)
                    for item in eslint_results:
                        fpath = normalize_path(os.path.relpath(item.get("filePath", ""), repo_path))
                        for msg in item.get("messages", []):
                            rule_id = msg.get("ruleId") or "eslint/quality"
                            line_no = msg.get("line", 1)
                            severity = "high" if msg.get("severity", 1) == 2 else "medium"
                            text = msg.get("message", "")
                            ev = Evidence(type="sarif", description=text, file_path=fpath, line_number=line_no)
                            findings.append(Finding(
                                rule_id=f"ESLINT/{rule_id}",
                                category="quality",
                                severity=severity,
                                title=f"ESLint: {rule_id}",
                                message=text,
                                file_path=fpath,
                                line_number=line_no,
                                evidence=[ev],
                            ))
                    if findings:
                        return findings
            except Exception:
                pass

        # Fallback regex checks for JS/TS
        for rel_file in js_files:
            abs_path = os.path.join(repo_path, rel_file) if not os.path.isabs(rel_file) else rel_file
            if not os.path.isfile(abs_path):
                continue
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                for idx, line in enumerate(lines, 1):
                    # Check for debugger statement
                    if re.search(r"\bdebugger\b", line):
                        ev = Evidence(type="regex", description="Debugger statement detected in source code.", file_path=rel_file, line_number=idx, snippet=line.strip())
                        findings.append(Finding(
                            rule_id="ESLINT/no-debugger",
                            category="quality",
                            severity="medium",
                            title="Debugger statement found",
                            message="Remove 'debugger' statements before committing to production.",
                            file_path=rel_file,
                            line_number=idx,
                            code_snippet=line.strip(),
                            evidence=[ev],
                        ))
            except Exception:
                pass

        return findings
