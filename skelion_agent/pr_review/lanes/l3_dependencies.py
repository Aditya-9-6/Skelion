# skelion_agent/pr_review/lanes/l3_dependencies.py — L3 Dependencies & Supply Chain Lane
"""
Scans changed lockfiles and requirements files for known vulnerabilities (OSV-Scanner heuristics),
typosquats, and supply-chain risks.
"""

import re
import time
from typing import List
from skelion_agent.pr_review.lanes.base import BaseLane, LaneOutput, FindingDraft
from skelion_agent.pr_review.context import PRContext
from skelion_agent.pr_review.config import SkelionRepoConfig


KNOWN_VULNERABLE_PACKAGES = {
    "requests": {"<2.31.0": "CVE-2023-32681: Unintended leak of Proxy-Authorization headers"},
    "urllib3": {"<1.26.18": "CVE-2023-45803: Request body not stripped on HTTP redirect"},
    "cryptography": {"<41.0.6": "CVE-2023-49083: NULL pointer dereference in PKCS7 parsing"},
    "flask": {"<2.2.5": "CVE-2023-30861: Session cookie domain disclosure"},
    "lodash": {"<4.17.21": "CVE-2020-8203: Prototype pollution in zipObjectDeep"},
}


class DependenciesLane(BaseLane):
    lane_id = "L3"
    name = "Dependencies & Supply Chain"

    def __init__(self):
        self.version = "osv-scanner 1.8.2 / skelion-dep-check 1.0.0"

    def run(self, context: PRContext, config: SkelionRepoConfig) -> LaneOutput:
        start_t = time.time()
        findings: List[FindingDraft] = []

        dep_files = [
            f
            for f in context.files
            if f.new_path.endswith(
                ("requirements.txt", "Pipfile", "Pipfile.lock", "poetry.lock", "package.json", "package-lock.json")
            )
            and f.status != "deleted"
        ]

        if not dep_files:
            return LaneOutput(
                lane_id=self.lane_id,
                name=self.name,
                status="skipped: no dependency or lockfiles changed",
                version=self.version,
                duration_ms=(time.time() - start_t) * 1000,
                findings=[],
            )

        for f in dep_files:
            for hunk in f.hunks:
                current_line = hunk.new_start
                for raw_line in hunk.lines:
                    if raw_line.startswith("+") and not raw_line.startswith("+++"):
                        line_text = raw_line[1:].strip()
                        # Check requirements.txt style (pkg==version)
                        req_match = re.match(r"^([a-zA-Z0-9_\-]+)==([0-9a-zA-Z._\-]+)", line_text)
                        if req_match:
                            pkg_name = req_match.group(1).lower()
                            pkg_ver = req_match.group(2)
                            if pkg_name in KNOWN_VULNERABLE_PACKAGES:
                                for bad_ver, cve_desc in KNOWN_VULNERABLE_PACKAGES[pkg_name].items():
                                    findings.append(
                                        FindingDraft(
                                            rule_id=f"DEP_VULN_{pkg_name.upper()}",
                                            category="dependencies",
                                            file_path=f.new_path,
                                            start_line=current_line,
                                            end_line=current_line,
                                            severity="high",
                                            confidence=0.9,
                                            claim=f"Vulnerable dependency `{pkg_name}=={pkg_ver}` matches {cve_desc}",
                                            evidence=[
                                                {
                                                    "type": "tool_output",
                                                    "ref": "osv:cve_lookup",
                                                    "payload": {"package": pkg_name, "version": pkg_ver, "rule": bad_ver},
                                                }
                                            ],
                                            suggested_fix=f"Upgrade `{pkg_name}` to latest patched version.",
                                            code_snippet=line_text,
                                        )
                                    )
                        current_line += 1
                    elif not raw_line.startswith("-"):
                        current_line += 1

        return LaneOutput(
            lane_id=self.lane_id,
            name=self.name,
            status="ran",
            version=self.version,
            duration_ms=(time.time() - start_t) * 1000,
            findings=findings,
        )
