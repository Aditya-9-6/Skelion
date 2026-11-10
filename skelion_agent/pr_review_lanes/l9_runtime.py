# skelion_agent/pr_review_lanes/l9_runtime.py — Runtime-Aware Impact Lane
"""
L9 Runtime-Aware Impact Lane:
Maps changed symbols to production routes, traffic share, error spikes, and incidents.
Reports 'skipped: no runtime data' if disconnected or telemetry data is missing.
"""

import ast
import os
from typing import Optional, Dict, Any, List, Set
from .base_lane import BaseLane
from .models import Finding, Evidence, compute_fingerprint
from .diff_parser import DiffParser, normalize_path
from .sarif_normalizer import resolve_enclosing_symbol


class L9RuntimeLane(BaseLane):
    """
    L9 Runtime-Aware Impact Adapter:
    Correlates PR diff and symbol modifications with live production metrics:
    - Route traffic share
    - Real-time error spikes
    - Active production incidents
    Calculates impact factors and boosts finding visibility for mission-critical paths.
    """

    def __init__(self, lane_id: str = "l9_runtime", name: str = "Runtime-Aware Impact Lane"):
        super().__init__(lane_id=lane_id, name=name, category="runtime")

    def get_tool_version(self) -> Optional[str]:
        return "skelion-runtime-telemetry-engine 1.0.0"

    def check_prerequisites(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Validates telemetry connection.
        Reports 'no runtime data' if disconnected or telemetry payload is missing.
        """
        if not context:
            return "no runtime data"

        runtime_data = context.get("runtime_data")
        if not runtime_data:
            return "no runtime data"

        if context.get("runtime_connected") is False:
            return "no runtime data"

        return None

    def execute(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []
        if not context:
            return findings

        runtime_data = context.get("runtime_data", {})
        routes_meta: Dict[str, Dict[str, Any]] = runtime_data.get("routes", {})
        incidents: List[Dict[str, Any]] = runtime_data.get("incidents", [])

        # Extract modified files and symbols from diff or target files
        changed_symbols = self._extract_changed_symbols(repo_path, diff)

        # Map changed symbols to routes
        for route_path, meta in routes_meta.items():
            traffic_share = float(meta.get("traffic_share", 0.0))
            error_spike = float(meta.get("error_spike_rate", 0.0))
            symbol_mappings = meta.get("symbol_mappings", [])

            # Check if any changed symbol matches this route
            matched_symbol: Optional[str] = None
            for sym in symbol_mappings:
                for cs in changed_symbols:
                    if sym.lower() in cs.lower() or cs.lower() in sym.lower():
                        matched_symbol = cs
                        break
                if matched_symbol:
                    break

            # If symbol matches, or route handler file was touched
            if matched_symbol:
                # Find matching incidents
                route_incidents = [
                    inc for inc in incidents if inc.get("route_path") == route_path
                ]

                # Compute impact factor:
                # Base traffic impact + error spike impact + incident impact
                impact_factor = 0.0
                if traffic_share >= 0.20:
                    impact_factor += 0.5
                if traffic_share >= 0.50:
                    impact_factor += 0.5
                if error_spike >= 0.05:
                    impact_factor += 0.8
                if route_incidents:
                    impact_factor += 1.0

                severity = "critical" if impact_factor >= 1.5 else ("high" if impact_factor >= 0.5 else "medium")

                # Find file path and line number for the matched symbol
                file_p = changed_symbols.get(matched_symbol, {}).get("file_path", "unknown")
                line_no = changed_symbols.get(matched_symbol, {}).get("line_number", 1)
                snip = changed_symbols.get(matched_symbol, {}).get("snippet", matched_symbol)

                ev = Evidence(
                    type="runtime",
                    description=(
                        f"Modified symbol '{matched_symbol}' routes to production endpoint '{route_path}' "
                        f"(traffic share: {traffic_share * 100:.1f}%, error rate: {error_spike * 100:.1f}%, "
                        f"incidents: {len(route_incidents)})."
                    ),
                    file_path=file_p,
                    line_number=line_no,
                    snippet=snip,
                    metadata={
                        "route": route_path,
                        "traffic_share": traffic_share,
                        "error_spike_rate": error_spike,
                        "incident_count": len(route_incidents),
                    },
                )

                finding = Finding(
                    rule_id="RUNTIME/high-impact-route-modified",
                    category="runtime",
                    severity=severity,
                    title=f"High Runtime Impact: Route '{route_path}' Modified",
                    message=(
                        f"Changes to '{matched_symbol}' directly affect production route '{route_path}' "
                        f"handling {traffic_share * 100:.1f}% of production traffic with {error_spike * 100:.1f}% error rate."
                    ),
                    file_path=file_p,
                    line_number=line_no,
                    code_snippet=snip,
                    enclosing_symbol=matched_symbol,
                    evidence=[ev],
                    confidence=1.0,
                    impact_factor=impact_factor,
                    metadata={
                        "route_path": route_path,
                        "traffic_share": traffic_share,
                        "error_spike_rate": error_spike,
                    },
                )
                findings.append(finding)

        return findings

    def _extract_changed_symbols(
        self,
        repo_path: str,
        diff: Optional[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Extracts modified function/class symbols and their locations."""
        symbols: Dict[str, Dict[str, Any]] = {}
        target_files = DiffParser.get_changed_files(diff) if diff is not None else []

        if not target_files:
            for root, _, files in os.walk(repo_path):
                if any(ig in root for ig in [".git", "node_modules", ".venv", "__pycache__"]):
                    continue
                for f in files:
                    if f.endswith(".py"):
                        target_files.append(normalize_path(os.path.relpath(os.path.join(root, f), repo_path)))

        for rel_file in target_files:
            abs_p = os.path.join(repo_path, rel_file) if not os.path.isabs(rel_file) else rel_file
            if not os.path.isfile(abs_p) or not rel_file.endswith(".py"):
                # Register file name as fallback symbol
                mod_sym = os.path.splitext(os.path.basename(rel_file))[0]
                symbols[mod_sym] = {"file_path": rel_file, "line_number": 1, "snippet": rel_file}
                continue

            try:
                with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                lines = content.splitlines()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        line_no = node.lineno
                        snip = lines[line_no - 1] if 0 < line_no <= len(lines) else node.name
                        symbols[node.name] = {
                            "file_path": rel_file,
                            "line_number": line_no,
                            "snippet": snip,
                        }
            except Exception:
                mod_sym = os.path.splitext(os.path.basename(rel_file))[0]
                symbols[mod_sym] = {"file_path": rel_file, "line_number": 1, "snippet": rel_file}

        return symbols
