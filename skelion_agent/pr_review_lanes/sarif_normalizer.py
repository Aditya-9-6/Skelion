# skelion_agent/pr_review_lanes/sarif_normalizer.py — Unified SARIF 2.1.0 Output Normalizer
"""
Converts SARIF 2.1.0 outputs into standard Finding models with stable fingerprints.
Supports outputs from Ruff, Semgrep, OSV-Scanner, CodeQL, and standard SARIF producers.
"""

import ast
import json
import os
import re
from typing import Dict, Any, List, Optional, Union
from .models import Finding, Evidence, compute_fingerprint
from .diff_parser import normalize_path


SARIF_LEVEL_TO_SEVERITY = {
    "error": "high",
    "warning": "medium",
    "note": "low",
    "none": "info",
}


def find_enclosing_symbol_python(content: str, line_number: int) -> Optional[str]:
    """Uses Python AST to find the deepest enclosing function or class symbol at line_number."""
    try:
        tree = ast.parse(content)
    except Exception:
        return None

    matching_symbols: List[str] = []

    def visit_node(node: ast.AST, prefix: str = ""):
        nonlocal matching_symbols
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = getattr(child, "lineno", 0)
                end = getattr(child, "end_lineno", getattr(child, "lineno", 0))
                full_name = f"{prefix}.{child.name}" if prefix else child.name
                if start <= line_number <= end:
                    matching_symbols.append(full_name)
                    visit_node(child, full_name)

    visit_node(tree)
    if matching_symbols:
        return matching_symbols[-1]
    return None


def find_enclosing_symbol_generic(lines: List[str], line_number: int) -> Optional[str]:
    """Heuristic fallback for finding enclosing function or class symbol in JS, TS, etc."""
    idx = max(0, min(len(lines) - 1, line_number - 1))
    func_pattern = re.compile(r"(?:function\s+([A-Za-z0-9_$]+)|(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_$]+)\s*=>|class\s+([A-Za-z0-9_$]+)|([A-Za-z0-9_$]+)\s*\([^)]*\)\s*\{)")
    for i in range(idx, -1, -1):
        line = lines[i]
        match = func_pattern.search(line)
        if match:
            for g in match.groups():
                if g:
                    return g
    return None


def resolve_enclosing_symbol(
    file_path: Optional[str],
    line_number: Optional[int],
    repo_path: Optional[str] = None,
    snippet: Optional[str] = None,
) -> Optional[str]:
    """Resolves the enclosing symbol for a given file and line number."""
    if not line_number or line_number <= 0:
        return None

    # Check if file exists on disk
    target_path = file_path
    if repo_path and file_path and not os.path.isabs(file_path):
        target_path = os.path.join(repo_path, file_path)

    if target_path and os.path.isfile(target_path):
        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if target_path.endswith(".py"):
                sym = find_enclosing_symbol_python(content, line_number)
                if sym:
                    return sym
            else:
                lines = content.splitlines()
                sym = find_enclosing_symbol_generic(lines, line_number)
                if sym:
                    return sym
        except Exception:
            pass

    # Fallback to module level symbol
    if file_path:
        base_name = os.path.basename(file_path)
        return f"{base_name}:<module>"
    return None


class SarifNormalizer:
    """Normalizes standard SARIF 2.1.0 data into unified Finding objects."""

    @classmethod
    def normalize(
        cls,
        sarif_data: Union[Dict[str, Any], str],
        default_category: str = "quality",
        repo_path: Optional[str] = None,
    ) -> List[Finding]:
        """Normalizes a SARIF dict or JSON string into a list of Finding objects."""
        if isinstance(sarif_data, str):
            try:
                sarif_dict = json.loads(sarif_data)
            except Exception:
                return []
        else:
            sarif_dict = sarif_data

        if not isinstance(sarif_dict, dict):
            return []

        runs = sarif_dict.get("runs", [])
        if not isinstance(runs, list):
            return []

        findings: List[Finding] = []

        for run in runs:
            if not isinstance(run, dict):
                continue

            tool = run.get("tool", {})
            driver = tool.get("driver", {})
            tool_name = driver.get("name", "Tool")
            tool_version = driver.get("version", "unknown")

            # Collect rules defined in driver
            rules_by_id: Dict[str, Dict[str, Any]] = {}
            for r in driver.get("rules", []):
                if isinstance(r, dict) and "id" in r:
                    rules_by_id[r["id"]] = r

            results = run.get("results", [])
            if not isinstance(results, list):
                continue

            for result in results:
                if not isinstance(result, dict):
                    continue

                raw_rule_id = result.get("ruleId") or result.get("rule", {}).get("id") or "SARIF_RULE"
                rule_meta = rules_by_id.get(raw_rule_id, {})
                rule_id = raw_rule_id

                if tool_name.lower() == "ruff" and not rule_id.startswith("RUFF/"):
                    rule_id = f"RUFF/{rule_id}"
                elif tool_name.lower() == "semgrep" and not rule_id.startswith("semgrep/"):
                    rule_id = f"semgrep/{rule_id}"

                # Extract message
                msg_obj = result.get("message", {})
                message_text = msg_obj.get("text", "") or rule_meta.get("shortDescription", {}).get("text", "") or "No message"

                # Extract level / severity
                sarif_level = result.get("level") or rule_meta.get("defaultConfiguration", {}).get("level", "warning")
                severity = SARIF_LEVEL_TO_SEVERITY.get(str(sarif_level).lower(), "medium")

                # Determine category
                category = default_category
                lower_rule = rule_id.lower()
                lower_tool = tool_name.lower()
                if "security" in lower_tool or "semgrep" in lower_tool or "gitleaks" in lower_tool or "cve" in lower_rule or "sec" in lower_rule:
                    category = "security"
                elif "osv" in lower_tool or "dependency" in lower_rule or "vulnerability" in lower_rule:
                    category = "dependency"
                elif "perf" in lower_rule or "performance" in lower_tool:
                    category = "performance"

                # Extract location details
                locations = result.get("locations", [])
                file_path = ""
                line_number: Optional[int] = None
                end_line: Optional[int] = None
                col_number: Optional[int] = None
                end_col: Optional[int] = None
                snippet_text: Optional[str] = None
                enclosing_symbol: Optional[str] = None

                if locations and isinstance(locations, list) and isinstance(locations[0], dict):
                    loc0 = locations[0]
                    phys = loc0.get("physicalLocation", {})
                    art = phys.get("artifactLocation", {})
                    raw_uri = art.get("uri", "")
                    file_path = normalize_path(raw_uri)

                    region = phys.get("region", {})
                    line_number = region.get("startLine")
                    end_line = region.get("endLine", line_number)
                    col_number = region.get("startColumn")
                    end_col = region.get("endColumn")

                    snip = region.get("snippet", {})
                    snippet_text = snip.get("text")

                    # Check logical locations for enclosing symbol
                    log_locs = loc0.get("logicalLocations", [])
                    if log_locs and isinstance(log_locs, list) and isinstance(log_locs[0], dict):
                        enclosing_symbol = log_locs[0].get("name") or log_locs[0].get("fullyQualifiedName")

                # If snippet is missing, try reading from disk
                if not snippet_text and file_path and line_number and repo_path:
                    abs_path = os.path.join(repo_path, file_path) if not os.path.isabs(file_path) else file_path
                    if os.path.isfile(abs_path):
                        try:
                            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                                all_lines = f.readlines()
                            if 0 < line_number <= len(all_lines):
                                snippet_text = all_lines[line_number - 1].strip()
                        except Exception:
                            pass

                # If enclosing symbol is missing, resolve it
                if not enclosing_symbol:
                    enclosing_symbol = resolve_enclosing_symbol(
                        file_path=file_path,
                        line_number=line_number,
                        repo_path=repo_path,
                        snippet=snippet_text,
                    )

                # Normalized code snippet
                norm_snippet = " ".join((snippet_text or "").split()) if snippet_text else ""

                # Compute stable fingerprint:
                # fingerprint = hash(rule_id_or_category, normalized_code_snippet, enclosing_symbol, file_path_at_symbol_level)
                fingerprint = compute_fingerprint(
                    rule_id_or_category=rule_id,
                    normalized_code_snippet=norm_snippet,
                    enclosing_symbol=enclosing_symbol,
                    file_path=file_path,
                )

                # Create verifiable evidence item
                evidence = Evidence(
                    type="sarif",
                    description=f"[{tool_name} {rule_id}] {message_text}",
                    file_path=file_path,
                    line_number=line_number,
                    end_line=end_line,
                    snippet=snippet_text,
                    metadata={
                        "tool": tool_name,
                        "tool_version": tool_version,
                        "rule_id": rule_id,
                        "sarif_level": sarif_level,
                    },
                )

                finding = Finding(
                    rule_id=rule_id,
                    category=category,
                    severity=severity,
                    title=f"[{tool_name}] {rule_id}",
                    message=message_text,
                    file_path=file_path,
                    line_number=line_number,
                    end_line=end_line,
                    column_number=col_number,
                    end_column=end_col,
                    code_snippet=snippet_text,
                    normalized_code_snippet=norm_snippet,
                    enclosing_symbol=enclosing_symbol,
                    fingerprint=fingerprint,
                    evidence=[evidence],
                    confidence=1.0,
                    evidence_strength=1.0,
                    metadata={
                        "tool": tool_name,
                        "tool_version": tool_version,
                    },
                )
                findings.append(finding)

        return findings
