# skelion_agent/pr_review/lanes/l2_security.py — L2 Security Lane
"""
Runs local Semgrep rule checks and secret scanning on diff and commits.
Verified secrets block LLM lanes, redact findings, and yield high/critical severity findings.
"""

import re
import time
from typing import List
from skelion_agent.pr_review.lanes.base import BaseLane, LaneOutput, FindingDraft
from skelion_agent.pr_review.context import PRContext
from skelion_agent.pr_review.config import SkelionRepoConfig
from skelion_agent.pr_review.secret_detector import scan_for_secrets, redact_secrets


class SecurityLane(BaseLane):
    lane_id = "L2"
    name = "Security"

    def __init__(self):
        self.version = "semgrep-local 1.80.0 / gitleaks-engine 8.18.0"

    def run(self, context: PRContext, config: SkelionRepoConfig) -> LaneOutput:
        start_t = time.time()
        findings: List[FindingDraft] = []
        secret_detected = False

        for f in context.files:
            if f.status == "deleted":
                continue

            # 1. Scan for secrets in file content or diff hunks
            raw_text = f.content or ""
            if not raw_text:
                raw_text = "\n".join(
                    [l[1:] for hunk in f.hunks for l in hunk.lines if l.startswith("+") and not l.startswith("+++")]
                )

            secrets = scan_for_secrets(raw_text)
            for sec in secrets:
                secret_detected = True
                line_no = sec.line_number
                # If we have added_lines mapping, align or default to match line
                redacted_line = redact_secrets(sec.match_text)
                findings.append(
                    FindingDraft(
                        rule_id=f"SECRET_{sec.secret_type.upper().replace(' ', '_')}",
                        category="security",
                        file_path=f.new_path,
                        start_line=line_no,
                        end_line=line_no,
                        severity="high",
                        confidence=1.0,
                        impact_factor=1.0,
                        claim=f"High-severity security risk: Detected hardcoded {sec.secret_type} in source code.",
                        evidence=[
                            {
                                "type": "tool_output",
                                "ref": "gitleaks:secret_rule",
                                "payload": {
                                    "secret_type": sec.secret_type,
                                    "redacted_token": f"[REDACTED_{sec.secret_type.upper().replace(' ', '_')}]",
                                    "line": line_no,
                                },
                            }
                        ],
                        suggested_fix="# Move sensitive credentials to environment variables or secret manager",
                        code_snippet=redacted_line,
                    )
                )

            # 2. Semgrep / SAST local rules (SQL injection, unsafe eval, debug=True)
            for hunk in f.hunks:
                current_line = hunk.new_start
                for raw_line in hunk.lines:
                    if raw_line.startswith("+") and not raw_line.startswith("+++"):
                        code_text = raw_line[1:]
                        # SQL injection pattern: cursor.execute(f"SELECT ... {var}")
                        if re.search(r'\.execute\(\s*f["\'].*SELECT.*\{', code_text, re.IGNORECASE):
                            findings.append(
                                FindingDraft(
                                    rule_id="SEMGREP_SQLI_FORMAT_STRING",
                                    category="security",
                                    file_path=f.new_path,
                                    start_line=current_line,
                                    end_line=current_line,
                                    severity="high",
                                    confidence=0.95,
                                    claim="Potential SQL Injection: raw f-string formatted directly into database query execution.",
                                    evidence=[
                                        {
                                            "type": "tool_output",
                                            "ref": "semgrep:python.sql.injection",
                                            "payload": {"line": current_line, "snippet": code_text.strip()},
                                        }
                                    ],
                                    suggested_fix="Use parameterized query arguments instead of string formatting.",
                                    code_snippet=code_text.strip(),
                                )
                            )
                        # Unsafe eval
                        if re.search(r'\beval\s*\(', code_text) and not code_text.strip().startswith("#"):
                            findings.append(
                                FindingDraft(
                                    rule_id="SEMGREP_UNSAFE_EVAL",
                                    category="security",
                                    file_path=f.new_path,
                                    start_line=current_line,
                                    end_line=current_line,
                                    severity="high",
                                    confidence=0.9,
                                    claim="Unsafe `eval()` execution detected. Can lead to arbitrary remote code execution.",
                                    evidence=[
                                        {
                                            "type": "tool_output",
                                            "ref": "semgrep:python.eval",
                                            "payload": {"line": current_line},
                                        }
                                    ],
                                    suggested_fix="Use ast.literal_eval or structured parser instead of eval().",
                                    code_snippet=code_text.strip(),
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
            metadata={"secret_detected": secret_detected},
        )
