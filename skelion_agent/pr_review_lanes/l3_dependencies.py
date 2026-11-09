# skelion_agent/pr_review_lanes/l3_dependencies.py — OSV-Scanner & Dependency Safety Adapter
"""
L3 Dependencies Adapter:
1. OSV-Scanner adapter for changed lockfiles with SARIF normalization.
2. New-dependency safety checks:
   - Licensing checks (copyleft/restrictive licenses like GPL/AGPL).
   - Typosquat heuristics (Levenshtein distance, transposition against popular packages).
"""

import os
import re
import shutil
import subprocess
from typing import Optional, Dict, Any, List, Set, Tuple
from .base_lane import BaseLane
from .models import Finding, Evidence, compute_fingerprint
from .diff_parser import DiffParser, normalize_path
from .sarif_normalizer import SarifNormalizer


LOCKFILE_NAMES = {
    "requirements.txt",
    "poetry.lock",
    "pipfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "cargo.lock",
    "go.sum",
}

# Popular reference packages for typosquat detection
POPULAR_PACKAGES = {
    "python": [
        "requests", "urllib3", "numpy", "pandas", "flask", "django",
        "pydantic", "fastapi", "cryptography", "colorama", "boto3",
        "pytest", "sqlalchemy", "scipy", "httpx", "werkzeug", "wheel",
    ],
    "npm": [
        "lodash", "express", "react", "react-dom", "axios", "typescript",
        "webpack", "chalk", "moment", "async", "commander", "vue",
    ],
}

# Known copyleft or restrictive licenses
RESTRICTIVE_LICENSES = {
    "gpl-3.0": "GNU General Public License v3.0 (Copyleft)",
    "agpl-3.0": "GNU Affero General Public License v3.0 (Network Copyleft)",
    "gpl-2.0": "GNU General Public License v2.0 (Copyleft)",
    "sspl-1.0": "Server Side Public License (Non-OSI Restricted)",
}

# Known mock / built-in OSV vulnerability feed for deterministic detection
KNOWN_VULNERABLE_PACKAGES: Dict[str, List[Dict[str, Any]]] = {
    "requests": [
        {"max_version": "2.31.0", "cve": "CVE-2023-32681", "severity": "medium", "fix": "2.31.0", "desc": "Unintended leak of Proxy-Authorization header in redirects."}
    ],
    "urllib3": [
        {"max_version": "2.0.7", "cve": "CVE-2023-45803", "severity": "high", "fix": "2.0.7", "desc": "Request body not stripped after 303 redirect leading to leak."}
    ],
    "aiohttp": [
        {"max_version": "3.9.0", "cve": "CVE-2023-47627", "severity": "high", "fix": "3.9.0", "desc": "HTTP request smuggling via improper chunked transfer encoding."}
    ],
    "cryptography": [
        {"max_version": "42.0.0", "cve": "CVE-2023-49083", "severity": "high", "fix": "42.0.0", "desc": "NULL pointer dereference when parsing PKCS7 certificates."}
    ],
    "lodash": [
        {"max_version": "4.17.21", "cve": "CVE-2021-23337", "severity": "critical", "fix": "4.17.21", "desc": "Command injection via template function."}
    ],
}

# High-risk license database for specific packages
KNOWN_PACKAGE_LICENSES: Dict[str, str] = {
    "plone": "GPL-2.0",
    "pygpl": "GPL-3.0",
    "agpl-service": "AGPL-3.0",
    "ansible": "GPL-3.0",
    "mupdf": "AGPL-3.0",
}


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes Levenshtein edit distance between two strings."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0, v1 = v1, [0] * (len(s2) + 1)

    return v0[len(s2)]


def parse_version_tuple(v: str) -> Tuple[Any, ...]:
    """Parses a version string into a comparable tuple of ints and strings."""
    if not v:
        return ()
    clean_v = v.strip().lstrip("v")
    parts: List[Any] = []
    for seg in re.split(r"[.\-+]", clean_v):
        if seg.isdigit():
            parts.append(int(seg))
        elif seg:
            parts.append(seg)
    return tuple(parts)


def check_typosquatting(pkg_name: str) -> Optional[Tuple[str, int]]:
    """
    Checks if pkg_name is a likely typosquat of a popular package.
    Returns (popular_target, distance) if suspicious, or None.
    """
    clean_name = pkg_name.lower().strip()
    all_popular = POPULAR_PACKAGES["python"] + POPULAR_PACKAGES["npm"]

    if clean_name in all_popular:
        return None  # Exact legitimate package

    for pop in all_popular:
        dist = levenshtein_distance(clean_name, pop)
        # 1 or 2 character edits on popular package names >= 4 characters
        if 0 < dist <= 2 and len(pop) >= 4:
            # Check length ratio to avoid short false positives (e.g. 're' vs 'vue')
            if abs(len(clean_name) - len(pop)) <= 2:
                return (pop, dist)

    return None


class L3DependenciesLane(BaseLane):
    """
    L3 Dependency & Supply Chain Security Adapter:
    - OSV-Scanner on lockfiles
    - Typosquatting detection on added dependencies
    - Restrictive/copyleft licensing checks
    """

    def __init__(self, lane_id: str = "l3_dependencies", name: str = "Dependency Safety Lane"):
        super().__init__(lane_id=lane_id, name=name, category="dependency")
        self._cached_tool_version: Optional[str] = None

    def get_tool_version(self) -> Optional[str]:
        if self._cached_tool_version is not None:
            return self._cached_tool_version

        osv_path = shutil.which("osv-scanner")
        if osv_path:
            try:
                proc = subprocess.run([osv_path, "--version"], capture_output=True, encoding="utf-8", errors="replace", timeout=5)
                if proc.returncode == 0:
                    self._cached_tool_version = proc.stdout.strip()
                    return self._cached_tool_version
            except Exception:
                pass

        self._cached_tool_version = "builtin-osv-scanner 1.0.0"
        return self._cached_tool_version

    def check_prerequisites(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Skips if no lockfile or dependency manifests are modified in diff or present."""
        if diff is not None:
            changed_files = DiffParser.get_changed_files(diff)
            has_dep_file = any(
                os.path.basename(f).lower() in LOCKFILE_NAMES
                for f in changed_files
            )
            if not has_dep_file:
                return "no changed lockfiles or dependencies"
        else:
            found = False
            for root, _, files in os.walk(repo_path):
                if any(ig in root for ig in [".git", "node_modules", ".venv"]):
                    continue
                if any(f.lower() in LOCKFILE_NAMES for f in files):
                    found = True
                    break
            if not found:
                return "no changed lockfiles or dependencies"
        return None

    def execute(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []

        # Find lockfiles to inspect
        target_lockfiles: List[str] = []
        if diff is not None:
            changed = DiffParser.get_changed_files(diff)
            target_lockfiles = [
                f for f in changed if os.path.basename(f).lower() in LOCKFILE_NAMES
            ]
        else:
            for root, _, files in os.walk(repo_path):
                if any(ig in root for ig in [".git", "node_modules", ".venv"]):
                    continue
                for f in files:
                    if f.lower() in LOCKFILE_NAMES:
                        target_lockfiles.append(normalize_path(os.path.relpath(os.path.join(root, f), repo_path)))

        for rel_file in target_lockfiles:
            abs_path = os.path.join(repo_path, rel_file) if not os.path.isabs(rel_file) else rel_file
            if not os.path.isfile(abs_path):
                continue

            # 1. Run OSV-Scanner CLI or built-in OSV vulnerability check
            lockfile_findings = self._scan_lockfile_vulnerabilities(abs_path, rel_file, repo_path)
            findings.extend(lockfile_findings)

            # 2. Run new-dependency safety checks (licensing & typosquatting)
            safety_findings = self._check_new_dependency_safety(abs_path, rel_file, diff)
            findings.extend(safety_findings)

        return findings

    def _scan_lockfile_vulnerabilities(self, abs_path: str, rel_path: str, repo_path: str) -> List[Finding]:
        findings: List[Finding] = []
        osv_path = shutil.which("osv-scanner")

        if osv_path:
            try:
                cmd = [osv_path, "--format=sarif", f"--lockfile={abs_path}"]
                proc = subprocess.run(cmd, cwd=repo_path, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
                if proc.stdout and "{" in proc.stdout:
                    s_idx = proc.stdout.find("{")
                    e_idx = proc.stdout.rfind("}")
                    if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
                        sarif_f = SarifNormalizer.normalize(proc.stdout[s_idx:e_idx + 1], default_category="dependency", repo_path=repo_path)
                        if sarif_f:
                            return sarif_f
            except Exception:
                pass

        # Built-in OSV vulnerability engine
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for idx, line in enumerate(lines, 1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#"):
                    continue

                # Parse package and version e.g. "requests==2.28.0" or "requests>=2.0.0"
                match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*([=><~^]=?)\s*([0-9a-zA-Z\.\-]+)", clean_line)
                if match:
                    pkg_name = match.group(1).lower()
                    pkg_ver = match.group(3)

                    if pkg_name in KNOWN_VULNERABLE_PACKAGES:
                        for vuln in KNOWN_VULNERABLE_PACKAGES[pkg_name]:
                            # Semver comparison: If version is lower or equal to max_version
                            if parse_version_tuple(pkg_ver) <= parse_version_tuple(vuln["max_version"]):
                                cve = vuln["cve"]
                                sev = vuln["severity"]
                                fix = vuln["fix"]
                                desc = vuln["desc"]
                                rule_id = f"OSV/{cve}"
                                ev = Evidence(
                                    type="sarif",
                                    description=f"Known vulnerability {cve} affecting {pkg_name} {pkg_ver}: {desc}",
                                    file_path=rel_path,
                                    line_number=idx,
                                    snippet=clean_line,
                                    metadata={"cve": cve, "fixed_in": fix, "package": pkg_name},
                                )
                                findings.append(Finding(
                                    rule_id=rule_id,
                                    category="dependency",
                                    severity=sev,
                                    title=f"Vulnerable Dependency: {pkg_name} ({cve})",
                                    message=f"{pkg_name} {pkg_ver} is vulnerable to {cve}. Upgrade to >={fix}.",
                                    file_path=rel_path,
                                    line_number=idx,
                                    code_snippet=clean_line,
                                    enclosing_symbol=f"{rel_path}:{pkg_name}",
                                    evidence=[ev],
                                    confidence=1.0,
                                    fix_suggestion=f"Upgrade {pkg_name} to >={fix}",
                                ))
        except Exception:
            pass

        return findings

    def _check_new_dependency_safety(self, abs_path: str, rel_path: str, diff: Optional[str]) -> List[Finding]:
        findings: List[Finding] = []
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for idx, line in enumerate(lines, 1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#"):
                    continue

                match = re.match(r"^([a-zA-Z0-9_\-\.]+)", clean_line)
                if not match:
                    continue

                pkg_name = match.group(1).lower()

                # 1. Typosquatting Check
                typosquat_match = check_typosquatting(pkg_name)
                if typosquat_match:
                    target, dist = typosquat_match
                    ev = Evidence(
                        type="typosquat",
                        description=f"Package '{pkg_name}' has Levenshtein distance {dist} from popular package '{target}'.",
                        file_path=rel_path,
                        line_number=idx,
                        snippet=clean_line,
                        metadata={"target_package": target, "edit_distance": dist},
                    )
                    findings.append(Finding(
                        rule_id="DEPENDENCY/typosquat-risk",
                        category="dependency",
                        severity="high",
                        title=f"Potential Typosquatting Package: {pkg_name}",
                        message=f"Package '{pkg_name}' closely resembles popular package '{target}' (edit distance {dist}). Verify spelling to prevent supply chain attack.",
                        file_path=rel_path,
                        line_number=idx,
                        code_snippet=clean_line,
                        enclosing_symbol=f"{rel_path}:{pkg_name}",
                        evidence=[ev],
                        confidence=0.9,
                        fix_suggestion=f"Verify if you intended to install '{target}' instead of '{pkg_name}'.",
                    ))

                # 2. Licensing Safety Check
                if pkg_name in KNOWN_PACKAGE_LICENSES:
                    lic = KNOWN_PACKAGE_LICENSES[pkg_name]
                    lic_lower = lic.lower()
                    if any(rest in lic_lower for rest in RESTRICTIVE_LICENSES):
                        ev = Evidence(
                            type="license",
                            description=f"Package '{pkg_name}' is licensed under restrictive copyleft license '{lic}'.",
                            file_path=rel_path,
                            line_number=idx,
                            snippet=clean_line,
                            metadata={"license": lic},
                        )
                        findings.append(Finding(
                            rule_id="DEPENDENCY/restrictive-license",
                            category="dependency",
                            severity="high",
                            title=f"Incompatible Copyleft License ({lic})",
                            message=f"Package '{pkg_name}' is licensed under '{lic}', which may impose copyleft contamination on proprietary code.",
                            file_path=rel_path,
                            line_number=idx,
                            code_snippet=clean_line,
                            enclosing_symbol=f"{rel_path}:{pkg_name}",
                            evidence=[ev],
                            confidence=1.0,
                            fix_suggestion=f"Replace '{pkg_name}' with a permissively licensed alternative (MIT, Apache-2.0, BSD).",
                        ))
        except Exception:
            pass

        return findings
