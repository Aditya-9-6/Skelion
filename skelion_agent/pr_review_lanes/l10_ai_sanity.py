# skelion_agent/pr_review_lanes/l10_ai_sanity.py — AI-Code Sanity Checker Adapter
"""
L10 AI-Code Sanity Checker:
Specifically targets common LLM-generated code errors:
1. Hallucinated imports that do not resolve in the locked environment or repo.
2. Non-existent methods on known types (e.g., str.reverse(), list.to_dict(), json.stringify()).
3. Large duplicate code blocks (copy-paste bloat).
"""

import ast
import importlib.util
import os
import re
import sys
from typing import Optional, Dict, Any, List, Set, Tuple
from .base_lane import BaseLane
from .models import Finding, Evidence, compute_fingerprint
from .diff_parser import DiffParser, normalize_path
from .sarif_normalizer import resolve_enclosing_symbol


# Known hallucinated methods on standard types
HALLUCINATED_TYPE_METHODS: Dict[str, Dict[str, str]] = {
    "str": {
        "reverse": "Use slicing '[::-1]' instead of .reverse().",
        "contains": "Use 'in' operator ('sub in s') instead of .contains().",
        "to_upper": "Use .upper() instead of .to_upper().",
        "to_lower": "Use .lower() instead of .to_lower().",
        "substr": "Use string slicing '[start:end]' instead of .substr().",
        "charAt": "Use indexing 's[i]' instead of .charAt().",
        "length": "Use len(s) instead of .length().",
    },
    "list": {
        "to_dict": "Use dict() constructor or dictionary comprehension instead of .to_dict().",
        "add": "Use .append() or .extend() instead of .add().",
        "push": "Use .append() instead of .push().",
        "contains": "Use 'in' operator ('item in lst') instead of .contains().",
        "size": "Use len(lst) instead of .size().",
        "delete": "Use del lst[i] or .remove(item) instead of .delete().",
    },
    "dict": {
        "append": "Use dict[key] = val or .update() instead of .append().",
        "add": "Use dict[key] = val or .update() instead of .add().",
        "push": "Use dict[key] = val or .update() instead of .push().",
        "size": "Use len(d) instead of .size().",
        "contains": "Use 'key in d' instead of .contains().",
    },
    "set": {
        "append": "Use .add() instead of .append() on set.",
        "push": "Use .add() instead of .push() on set.",
    },
    "json": {
        "stringify": "Use json.dumps() instead of JavaScript's json.stringify().",
        "parse": "Use json.loads() instead of JavaScript's json.parse().",
    },
}


class L10AiSanityLane(BaseLane):
    """
    L10 AI-Code Sanity Checker:
    Detects hallucinated imports, non-existent methods on standard types,
    and large duplicate code blocks produced by AI code assistants.
    """

    def __init__(self, lane_id: str = "l10_ai_sanity", name: str = "AI-Code Sanity Checker Lane"):
        super().__init__(lane_id=lane_id, name=name, category="ai_sanity")

    def get_tool_version(self) -> Optional[str]:
        return "skelion-ai-sanity-guard 1.0.0"

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
                return "no python files to analyze for ai sanity"
        return None

    def execute(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []
        target_files = self._get_target_files(repo_path, diff)
        repo_modules = self._collect_repo_modules(repo_path)
        requirements_pkgs = self._collect_declared_packages(repo_path)

        for rel_file in target_files:
            abs_path = os.path.join(repo_path, rel_file) if not os.path.isabs(rel_file) else rel_file
            if not os.path.isfile(abs_path):
                continue
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                # 1. Check Hallucinated Imports
                import_findings = self._check_hallucinated_imports(
                    rel_file, content, repo_path, repo_modules, requirements_pkgs
                )
                findings.extend(import_findings)

                # 2. Check Non-Existent Methods on Types
                method_findings = self._check_non_existent_methods(rel_file, content, repo_path)
                findings.extend(method_findings)

                # 3. Check Large Duplicate Code Blocks
                dup_findings = self._check_duplicate_code_blocks(rel_file, content, repo_path)
                findings.extend(dup_findings)

            except Exception:
                pass

        return findings

    def _get_target_files(self, repo_path: str, diff: Optional[str]) -> List[str]:
        if diff is not None:
            changed = DiffParser.get_changed_files(diff)
            return [normalize_path(f) for f in changed if f.endswith(".py")]

        files_list: List[str] = []
        for root, _, files in os.walk(repo_path):
            if any(ig in root for ig in [".git", "node_modules", ".venv", "__pycache__"]):
                continue
            for f in files:
                if f.endswith(".py"):
                    files_list.append(normalize_path(os.path.relpath(os.path.join(root, f), repo_path)))
        return files_list

    def _collect_repo_modules(self, repo_path: str) -> Set[str]:
        modules: Set[str] = set()
        try:
            for item in os.listdir(repo_path):
                full = os.path.join(repo_path, item)
                if os.path.isdir(full) and not item.startswith("."):
                    modules.add(item)
                elif item.endswith(".py"):
                    modules.add(item[:-3])
        except Exception:
            pass
        return modules

    def _collect_declared_packages(self, repo_path: str) -> Set[str]:
        pkgs: Set[str] = set()
        req_file = os.path.join(repo_path, "requirements.txt")
        if os.path.isfile(req_file):
            try:
                with open(req_file, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            m = re.match(r"^([a-zA-Z0-9_\-]+)", line)
                            if m:
                                name = m.group(1).lower().replace("-", "_")
                                pkgs.add(name)
            except Exception:
                pass
        return pkgs

    def _check_hallucinated_imports(
        self,
        file_path: str,
        content: str,
        repo_path: str,
        repo_modules: Set[str],
        declared_pkgs: Set[str],
    ) -> List[Finding]:
        findings: List[Finding] = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=file_path)
        except Exception:
            return findings

        # Standard library modules
        stdlib_names = getattr(sys, "stdlib_module_names", set())

        for node in ast.walk(tree):
            imported_names: List[Tuple[str, int]] = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    imported_names.append((top, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    top = node.module.split(".")[0]
                    imported_names.append((top, node.lineno))

            for mod_name, line_no in imported_names:
                mod_clean = mod_name.lower().replace("-", "_")
                # 1. Stdlib check
                if mod_name in stdlib_names or mod_name in sys.builtin_module_names:
                    continue
                # 2. Local repo check
                if mod_name in repo_modules or mod_clean in repo_modules:
                    continue
                # 3. Requirements check
                if mod_clean in declared_pkgs:
                    continue
                # 4. Environment check (find_spec)
                try:
                    spec = importlib.util.find_spec(mod_name)
                    if spec is not None:
                        continue
                except Exception:
                    pass

                # If none resolved, flag hallucinated import
                snip = lines[line_no - 1] if 0 < line_no <= len(lines) else f"import {mod_name}"
                sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
                ev = Evidence(
                    type="ast",
                    description=f"Imported module '{mod_name}' cannot be resolved in standard library, installed packages, or repository.",
                    file_path=file_path,
                    line_number=line_no,
                    snippet=snip,
                    metadata={"unresolved_module": mod_name},
                )
                findings.append(Finding(
                    rule_id="AI/hallucinated-import",
                    category="ai_sanity",
                    severity="high",
                    title=f"Hallucinated Import: '{mod_name}'",
                    message=f"Module '{mod_name}' does not exist in standard library, local modules, or declared dependencies. LLM likely hallucinated this package.",
                    file_path=file_path,
                    line_number=line_no,
                    code_snippet=snip,
                    enclosing_symbol=sym,
                    evidence=[ev],
                    confidence=0.95,
                    fix_suggestion=f"Install '{mod_name}' or replace with an existing library.",
                ))

        return findings

    def _check_non_existent_methods(self, file_path: str, content: str, repo_path: str) -> List[Finding]:
        findings: List[Finding] = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=file_path)
        except Exception:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr
                val_node = node.func.value
                matched_type: Optional[str] = None

                # Check json module calls: json.stringify() or json.parse()
                if isinstance(val_node, ast.Name) and val_node.id == "json":
                    if attr_name in HALLUCINATED_TYPE_METHODS.get("json", {}):
                        matched_type = "json"

                # Check string literals: e.g. "foo".reverse() or 'abc'.contains(...)
                elif isinstance(val_node, ast.Constant) and isinstance(val_node.value, str):
                    if attr_name in HALLUCINATED_TYPE_METHODS.get("str", {}):
                        matched_type = "str"

                # Check list literals: e.g. [1, 2].to_dict() or [].push(x)
                elif isinstance(val_node, ast.List):
                    if attr_name in HALLUCINATED_TYPE_METHODS.get("list", {}):
                        matched_type = "list"

                # Check dict literals: e.g. {}.append(x)
                elif isinstance(val_node, ast.Dict):
                    if attr_name in HALLUCINATED_TYPE_METHODS.get("dict", {}):
                        matched_type = "dict"

                # Check named variables with common type suffixes: my_str.reverse() or items_list.to_dict()
                elif isinstance(val_node, ast.Name):
                    var_name = val_node.id.lower()
                    if var_name.endswith(("_str", "_text", "string")) and attr_name in HALLUCINATED_TYPE_METHODS.get("str", {}):
                        matched_type = "str"
                    elif var_name.endswith(("_list", "items", "elements", "_arr")) and attr_name in HALLUCINATED_TYPE_METHODS.get("list", {}):
                        matched_type = "list"
                    elif var_name.endswith(("_dict", "_map", "_data")) and attr_name in HALLUCINATED_TYPE_METHODS.get("dict", {}):
                        matched_type = "dict"

                if matched_type:
                    rec = HALLUCINATED_TYPE_METHODS[matched_type][attr_name]
                    line_no = node.lineno
                    snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                    sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
                    ev = Evidence(
                        type="ast",
                        description=f"Type '{matched_type}' has no method '{attr_name}'.",
                        file_path=file_path,
                        line_number=line_no,
                        snippet=snip,
                        metadata={"type": matched_type, "method": attr_name},
                    )
                    findings.append(Finding(
                        rule_id="AI/non-existent-method",
                        category="ai_sanity",
                        severity="high",
                        title=f"Non-Existent Method on Type '{matched_type}': .{attr_name}()",
                        message=f"Type '{matched_type}' does not have method '{attr_name}'. {rec}",
                        file_path=file_path,
                        line_number=line_no,
                        code_snippet=snip,
                        enclosing_symbol=sym,
                        evidence=[ev],
                        confidence=0.95,
                        fix_suggestion=rec,
                    ))

        return findings

    def _check_duplicate_code_blocks(self, file_path: str, content: str, repo_path: str) -> List[Finding]:
        findings: List[Finding] = []
        raw_lines = content.splitlines()
        normalized_lines = [l.strip() for l in raw_lines]

        # Look for duplicate chunks of 6+ consecutive non-trivial lines
        chunk_size = 6
        seen_chunks: Dict[str, int] = {}

        for i in range(len(normalized_lines) - chunk_size + 1):
            chunk_slice = normalized_lines[i : i + chunk_size]
            # Skip empty or trivial chunks
            if any(l in ("", "{", "}", "pass", "return", "continue") for l in chunk_slice):
                continue
            chunk_str = "\n".join(chunk_slice)
            if len(chunk_str) < 60:
                continue

            line_no = i + 1
            if chunk_str in seen_chunks:
                prev_line = seen_chunks[chunk_str]
                if line_no - prev_line >= chunk_size:  # Non-overlapping
                    snip = "\n".join(raw_lines[i : i + 3])
                    sym = resolve_enclosing_symbol(file_path, line_no, repo_path, snip)
                    ev = Evidence(
                        type="ast",
                        description=f"Duplicate code block of {chunk_size} lines identical to lines {prev_line}-{prev_line + chunk_size - 1}.",
                        file_path=file_path,
                        line_number=line_no,
                        snippet=snip,
                        metadata={"duplicate_of_line": prev_line, "block_size": chunk_size},
                    )
                    findings.append(Finding(
                        rule_id="AI/large-duplicate-code-block",
                        category="ai_sanity",
                        severity="medium",
                        title="Large Duplicate Code Block Detected",
                        message=f"Duplicate code block of {chunk_size} lines detected at line {line_no} (identical to lines {prev_line}-{prev_line + chunk_size - 1}). Extract into reusable helper.",
                        file_path=file_path,
                        line_number=line_no,
                        code_snippet=snip,
                        enclosing_symbol=sym,
                        evidence=[ev],
                        confidence=0.9,
                        fix_suggestion="Extract duplicated logic into a shared helper function.",
                    ))
                    break  # Limit to 1 duplicate finding per file to prevent flood
            else:
                seen_chunks[chunk_str] = line_no

        return findings
