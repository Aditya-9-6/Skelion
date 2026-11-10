# skelion_agent/pr_review_lanes/l7_performance.py — Static Performance Rules Adapter
"""
L7 Performance Lane:
Static performance rules detecting:
1. N+1 queries (DB query execution inside loops).
2. Blocking calls in async handlers (time.sleep, requests.*, subprocess in async def).
3. Unbounded loops and queries (queries missing LIMIT, while True without break).
"""

import ast
import os
from typing import Optional, Dict, Any, List, Tuple
from .base_lane import BaseLane
from .models import Finding, Evidence, compute_fingerprint
from .diff_parser import DiffParser, normalize_path
from .sarif_normalizer import resolve_enclosing_symbol


BLOCKING_ASYNC_CALLS = {
    ("time", "sleep"): "asyncio.sleep",
    ("requests", "get"): "httpx.AsyncClient.get",
    ("requests", "post"): "httpx.AsyncClient.post",
    ("requests", "put"): "httpx.AsyncClient.put",
    ("requests", "delete"): "httpx.AsyncClient.delete",
    ("requests", "request"): "httpx.AsyncClient.request",
    ("subprocess", "run"): "asyncio.create_subprocess_exec",
    ("subprocess", "call"): "asyncio.create_subprocess_exec",
    ("os", "system"): "asyncio.create_subprocess_shell",
}

DB_QUERY_METHODS = {
    "execute", "exec", "query", "raw", "select"
}


class L7PerformanceLane(BaseLane):
    """
    L7 Performance Adapter:
    Static analysis for N+1 queries, blocking calls in async handlers, and unbounded queries.
    """

    def __init__(self, lane_id: str = "l7_performance", name: str = "Static Performance Lane"):
        super().__init__(lane_id=lane_id, name=name, category="performance")

    def get_tool_version(self) -> Optional[str]:
        return "skelion-ast-performance-checker 1.0.0"

    def check_prerequisites(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if diff is not None:
            changed_files = DiffParser.get_changed_files(diff)
            py_files = [f for f in changed_files if f.endswith(".py")]
            if not py_files:
                return "no python files to analyze for performance"
        return None

    def execute(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []
        target_files: List[str] = []

        if diff is not None:
            changed = DiffParser.get_changed_files(diff)
            target_files = [f for f in changed if f.endswith(".py")]
        else:
            for root, _, files in os.walk(repo_path):
                if any(ig in root for ig in [".git", "node_modules", ".venv", "__pycache__"]):
                    continue
                for f in files:
                    if f.endswith(".py"):
                        target_files.append(normalize_path(os.path.relpath(os.path.join(root, f), repo_path)))

        for rel_file in target_files:
            abs_path = os.path.join(repo_path, rel_file) if not os.path.isabs(rel_file) else rel_file
            if not os.path.isfile(abs_path):
                continue
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                file_findings = self._analyze_performance_ast(rel_file, content, repo_path)
                findings.extend(file_findings)
            except Exception:
                pass

        return findings

    def _analyze_performance_ast(self, file_path: str, content: str, repo_path: str) -> List[Finding]:
        findings: List[Finding] = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=file_path)
        except Exception:
            return findings

        # Visitor to inspect AST
        for node in ast.walk(tree):
            # 1. Detect N+1 queries: DB queries inside loops (for / while)
            if isinstance(node, (ast.For, ast.While)):
                for inner_node in ast.walk(node):
                    if isinstance(inner_node, ast.Call):
                        if isinstance(inner_node.func, ast.Attribute):
                            attr_name = inner_node.func.attr
                            if attr_name in DB_QUERY_METHODS:
                                line_no = inner_node.lineno
                                snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                                sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
                                ev = Evidence(
                                    type="ast",
                                    description=f"Database query invocation '.{attr_name}()' inside loop structure.",
                                    file_path=file_path,
                                    line_number=line_no,
                                    snippet=snip,
                                    metadata={"query_method": attr_name},
                                )
                                findings.append(Finding(
                                    rule_id="PERF/n-plus-one-query",
                                    category="performance",
                                    severity="high",
                                    title=f"Potential N+1 Query in Loop: .{attr_name}()",
                                    message=f"Database query '{snip.strip()}' is executed inside a loop. Batch queries or use join/in_() to prevent N+1 overhead.",
                                    file_path=file_path,
                                    line_number=line_no,
                                    code_snippet=snip,
                                    enclosing_symbol=sym,
                                    evidence=[ev],
                                    confidence=0.9,
                                    fix_suggestion="Refactor query outside the loop or fetch batch using SQL IN (...) / JOIN.",
                                ))

            # 2. Detect Blocking calls inside async handlers
            if isinstance(node, ast.AsyncFunctionDef):
                async_func_name = node.name
                for inner_node in ast.walk(node):
                    if isinstance(inner_node, ast.Call):
                        call_match = self._check_blocking_call(inner_node)
                        if call_match:
                            callee_name, async_alt = call_match
                            line_no = inner_node.lineno
                            snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                            ev = Evidence(
                                type="ast",
                                description=f"Synchronous blocking call '{callee_name}' inside async function '{async_func_name}'.",
                                file_path=file_path,
                                line_number=line_no,
                                snippet=snip,
                                metadata={"blocking_call": callee_name, "async_alternative": async_alt},
                            )
                            findings.append(Finding(
                                rule_id="PERF/blocking-call-in-async",
                                category="performance",
                                severity="high",
                                title=f"Blocking Call in Async Handler: {callee_name}",
                                message=f"Synchronous '{callee_name}' halts the event loop in async function '{async_func_name}'. Replace with '{async_alt}'.",
                                file_path=file_path,
                                line_number=line_no,
                                code_snippet=snip,
                                enclosing_symbol=f"{async_func_name}",
                                evidence=[ev],
                                confidence=1.0,
                                fix_suggestion=f"Replace '{callee_name}' with '{async_alt}'.",
                            ))

            # 3. Detect Unbounded Loops: while True / while 1 with no break/return/raise
            if isinstance(node, ast.While):
                is_infinite_condition = False
                if isinstance(node.test, ast.Constant) and node.test.value in (True, 1):
                    is_infinite_condition = True
                elif isinstance(node.test, ast.Name) and node.test.id == "True":
                    is_infinite_condition = True

                if is_infinite_condition:
                    has_exit = any(
                        isinstance(sub, (ast.Break, ast.Return, ast.Raise))
                        for sub in ast.walk(node)
                    )
                    if not has_exit:
                        line_no = node.lineno
                        snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                        sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
                        ev = Evidence(
                            type="ast",
                            description="Unbounded 'while True' loop without break, return, or raise statement.",
                            file_path=file_path,
                            line_number=line_no,
                            snippet=snip,
                        )
                        findings.append(Finding(
                            rule_id="PERF/unbounded-loop",
                            category="performance",
                            severity="medium",
                            title="Unbounded Infinite Loop Detected",
                            message="Infinite loop without termination condition or break statement can freeze worker process.",
                            file_path=file_path,
                            line_number=line_no,
                            code_snippet=snip,
                            enclosing_symbol=sym,
                            evidence=[ev],
                            confidence=0.9,
                            fix_suggestion="Add a termination condition or timeout break guard.",
                        ))

            # 4. Detect Unbounded Queries: e.g. session.exec(select(Model)).all()
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "all":
                    # Check if caller looks like a query
                    line_no = node.lineno
                    snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                    if any(term in snip for term in ("select(", ".query(", "session.exec(")):
                        if "limit(" not in snip.lower() and "offset" not in snip.lower():
                            sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
                            ev = Evidence(
                                type="ast",
                                description="Query fetching all records (.all()) without pagination or limit.",
                                file_path=file_path,
                                line_number=line_no,
                                snippet=snip,
                            )
                            findings.append(Finding(
                                rule_id="PERF/unbounded-query",
                                category="performance",
                                severity="medium",
                                title="Unbounded Query without LIMIT",
                                message=f"Query '{snip.strip()}' fetches all rows without .limit() or pagination.",
                                file_path=file_path,
                                line_number=line_no,
                                code_snippet=snip,
                                enclosing_symbol=sym,
                                evidence=[ev],
                                confidence=0.8,
                                fix_suggestion="Add .limit(N) or cursor pagination to bound query memory consumption.",
                            ))

        return findings

    def _check_blocking_call(self, call_node: ast.Call) -> Optional[Tuple[str, str]]:
        if isinstance(call_node.func, ast.Attribute):
            attr = call_node.func.attr
            if isinstance(call_node.func.value, ast.Name):
                mod = call_node.func.value.id
                key = (mod, attr)
                if key in BLOCKING_ASYNC_CALLS:
                    return f"{mod}.{attr}", BLOCKING_ASYNC_CALLS[key]
        elif isinstance(call_node.func, ast.Name):
            name = call_node.func.id
            if name == "open":
                return "open()", "aiofiles.open()"
        return None
