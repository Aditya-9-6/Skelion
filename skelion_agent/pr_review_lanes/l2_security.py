# skelion_agent/pr_review_lanes/l2_security.py — Security Adapter & Pre-Prompt Secret Redaction
"""
L2 Security Adapter:
1. Semgrep runner with --metrics=off and vendored/local rules (local_rules.yaml).
2. Gitleaks runner on diff & new commits for leaked secrets.
3. Pre-prompt secret detection and automatic redaction before any LLM prompt construction.
"""

import ast
import os
import re
import shutil
import subprocess
from typing import Optional, Dict, Any, List, Tuple
from .base_lane import BaseLane
from .models import Finding, Evidence, compute_fingerprint
from .diff_parser import DiffParser, normalize_path
from .sarif_normalizer import SarifNormalizer, resolve_enclosing_symbol


# ---------------------------------------------------------------------------
# High-Risk Secret Patterns for Gitleaks & Pre-Prompt Redaction
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    # AWS Access Key ID
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ABIA|ACCA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # GitHub Personal Access Token
    ("GITHUB_PAT", re.compile(r"\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b"), "[REDACTED_GITHUB_PAT]"),
    # Skelion Live & Test API Keys
    ("SKELION_KEY", re.compile(r"\bskl_(?:live|test)_[a-zA-Z0-9]{16,40}\b"), "[REDACTED_SKELION_KEY]"),
    # OpenAI API Key
    ("OPENAI_KEY", re.compile(r"\bsk-(?:proj-|live-)?[a-zA-Z0-9]{20,60}\b"), "[REDACTED_API_KEY]"),
    # Anthropic API Key
    ("ANTHROPIC_KEY", re.compile(r"\bsk-ant-[a-zA-Z0-9_\-]{20,60}\b"), "[REDACTED_API_KEY]"),
    # Stripe Secret Key
    ("STRIPE_KEY", re.compile(r"\brk_live_[a-zA-Z0-9]{24,34}|sk_live_[a-zA-Z0-9]{24,34}\b"), "[REDACTED_API_KEY]"),
    # Slack Token
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}\b"), "[REDACTED_API_KEY]"),
    # JWT Token
    ("JWT_TOKEN", re.compile(r"\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b"), "[REDACTED_JWT]"),
    # Private Key Headers
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[^-]+-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
    # Generic Assignment Secrets: api_key = "..."
    ("ASSIGNED_SECRET", re.compile(r"""(?i)(?:secret_key|api_key|password|jwt_secret|auth_token)\s*=\s*['"]([a-zA-Z0-9_\-\.]{16,})['"]"""), "[REDACTED_GENERIC_SECRET]"),
]


class SecretRedactor:
    """Detects secrets and performs automatic redaction before any LLM prompt construction."""

    @classmethod
    def redact_prompt(cls, prompt_text: str) -> str:
        """Returns redacted prompt text safe for LLM ingestion."""
        redacted, _ = cls.detect_and_redact(prompt_text)
        return redacted

    @classmethod
    def detect_and_redact(
        cls,
        text: str,
        file_path: Optional[str] = None,
        base_line: int = 1,
    ) -> Tuple[str, List[Finding]]:
        """
        Detects secrets in text, masks them with safe placeholder tokens,
        and generates critical Finding instances for each detected secret.
        Uses exact non-overlapping spans and right-to-left replacement.
        """
        if not text:
            return text, []

        findings: List[Finding] = []
        matches: List[Tuple[int, int, str, str, str, int]] = []

        for sec_name, pattern, mask in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                if match.lastindex and match.lastindex >= 1:
                    start, end = match.span(1)
                    secret_val = match.group(1)
                else:
                    start, end = match.span(0)
                    secret_val = match.group(0)

                line_offset = text[:start].count("\n")
                line_no = base_line + line_offset
                matches.append((start, end, mask, sec_name, secret_val, line_no))

        # Sort matches by start position ascending
        matches.sort(key=lambda m: m[0])

        # Filter out overlapping matches (keep earlier match)
        non_overlapping: List[Tuple[int, int, str, str, str, int]] = []
        last_end = -1
        for m in matches:
            start, end = m[0], m[1]
            if start >= last_end:
                non_overlapping.append(m)
                last_end = end

        # Build findings
        for start, end, mask, sec_name, secret_val, line_no in non_overlapping:
            masked_snippet = f"{sec_name}: {mask}"
            f_path = file_path or "prompt/llm_context"
            rule_id = f"GITLEAKS/{sec_name}"
            sym = f"prompt:{sec_name}"

            ev = Evidence(
                type="regex",
                description=f"Secret detected: {sec_name}. Redacted before LLM prompt transmission.",
                file_path=f_path,
                line_number=line_no,
                snippet=masked_snippet,
                metadata={"secret_type": sec_name},
            )

            finding = Finding(
                rule_id=rule_id,
                category="security",
                severity="critical",
                title=f"Hardcoded Secret Detected ({sec_name})",
                message=f"Detected high-entropy credential ({sec_name}). Pre-prompt redaction automatically masked it.",
                file_path=f_path,
                line_number=line_no,
                code_snippet=masked_snippet,
                enclosing_symbol=sym,
                evidence=[ev],
                confidence=1.0,
                evidence_strength=1.0,
                fix_suggestion="Move credential to an environment variable or secure vault.",
            )
            findings.append(finding)

        # Replace text slices right-to-left
        redacted_chars = list(text)
        for start, end, mask, _, _, _ in reversed(non_overlapping):
            redacted_chars[start:end] = list(mask)
        redacted_text = "".join(redacted_chars)

        return redacted_text, findings


def redact_prompt(text: str) -> str:
    """Convenience helper to redact secrets before LLM prompt construction."""
    return SecretRedactor.redact_prompt(text)


def detect_and_redact_secrets(text: str, file_path: Optional[str] = None) -> Tuple[str, List[Finding]]:
    """Convenience helper to detect and redact secrets."""
    return SecretRedactor.detect_and_redact(text, file_path=file_path)


class L2SecurityLane(BaseLane):
    """
    L2 Security Adapter:
    - Semgrep scan with --metrics=off and local_rules.yaml / vendored rules
    - Gitleaks secret detection across diff and files
    - Pre-prompt secret redaction helper integration
    """

    def __init__(
        self,
        lane_id: str = "l2_security",
        name: str = "Security Adapter Lane",
        rules_path: Optional[str] = None,
    ):
        super().__init__(lane_id=lane_id, name=name, category="security")
        self.rules_path = rules_path
        self._cached_tool_version: Optional[str] = None

    def get_tool_version(self) -> Optional[str]:
        if self._cached_tool_version is not None:
            return self._cached_tool_version

        versions: List[str] = []
        semgrep_path = shutil.which("semgrep")
        if semgrep_path:
            try:
                proc = subprocess.run([semgrep_path, "--version"], capture_output=True, encoding="utf-8", errors="replace", timeout=5)
                if proc.returncode == 0:
                    versions.append(f"semgrep {proc.stdout.strip()}")
            except Exception:
                versions.append("semgrep (available)")

        gitleaks_path = shutil.which("gitleaks")
        if gitleaks_path:
            try:
                proc = subprocess.run([gitleaks_path, "version"], capture_output=True, encoding="utf-8", errors="replace", timeout=5)
                if proc.returncode == 0:
                    versions.append(f"gitleaks {proc.stdout.strip()}")
            except Exception:
                versions.append("gitleaks (available)")

        if not versions:
            self._cached_tool_version = "builtin-security-engine 1.0.0"
        else:
            self._cached_tool_version = ", ".join(versions)

        return self._cached_tool_version

    def check_prerequisites(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        # Security lane runs on all code modifications
        return None

    def execute(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []

        # 1. Run Gitleaks / Secret detection on diff or files
        secret_findings = self._scan_secrets(repo_path, diff)
        findings.extend(secret_findings)

        # 2. Run Semgrep (with --metrics=off and local_rules.yaml) or built-in rule runner
        semgrep_findings = self._run_semgrep_or_builtin_rules(repo_path, diff)
        findings.extend(semgrep_findings)

        return findings

    def _scan_secrets(self, repo_path: str, diff: Optional[str]) -> List[Finding]:
        findings: List[Finding] = []

        # Try live Gitleaks CLI if available in environment
        gitleaks_path = shutil.which("gitleaks")
        if gitleaks_path:
            try:
                cmd = [gitleaks_path, "detect", "--no-git", f"--source={repo_path}", "--report-format=sarif", "--exit-code=0"]
                proc = subprocess.run(cmd, cwd=repo_path, capture_output=True, encoding="utf-8", errors="replace", timeout=20)
                if proc.stdout and "{" in proc.stdout:
                    s_idx = proc.stdout.find("{")
                    e_idx = proc.stdout.rfind("}")
                    if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
                        sarif_f = SarifNormalizer.normalize(proc.stdout[s_idx:e_idx + 1], default_category="security", repo_path=repo_path)
                        if sarif_f:
                            return sarif_f
            except Exception:
                pass

        # Check diff directly if provided
        if diff is not None:
            diff_lines = DiffParser.parse(diff)
            for fpath, lines in diff_lines.items():
                abs_p = os.path.join(repo_path, fpath) if not os.path.isabs(fpath) else fpath
                if os.path.isfile(abs_p):
                    try:
                        with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
                            file_content = f.read()
                        _, file_findings = SecretRedactor.detect_and_redact(file_content, file_path=fpath)
                        # Filter to only lines in diff
                        for item in file_findings:
                            if item.line_number in lines:
                                findings.append(item)
                    except Exception:
                        pass
                else:
                    # Scan diff text specifically for added lines in this file
                    curr_file = None
                    curr_line = 0
                    for d_line in diff.splitlines():
                        if d_line.startswith("diff --git"):
                            m = re.match(r"^diff --git a/(.*?) b/(.*?)$", d_line)
                            if m:
                                curr_file = normalize_path(m.group(2))
                        elif d_line.startswith("@@"):
                            m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", d_line)
                            if m:
                                curr_line = int(m.group(1))
                        elif curr_file == normalize_path(fpath):
                            if d_line.startswith("+") and not d_line.startswith("+++"):
                                _, line_f = SecretRedactor.detect_and_redact(d_line[1:], file_path=fpath, base_line=curr_line)
                                findings.extend(line_f)
                                curr_line += 1
                            elif not d_line.startswith("-"):
                                curr_line += 1
            return findings

        # Scan workspace files
        for root, _, files in os.walk(repo_path):
            if any(ig in root for ig in [".git", "node_modules", ".venv", "__pycache__"]):
                continue
            for f in files:
                if any(f.endswith(ext) for ext in [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env"]):
                    full = os.path.join(root, f)
                    rel = normalize_path(os.path.relpath(full, repo_path))
                    try:
                        with open(full, "r", encoding="utf-8", errors="replace") as fh:
                            content = fh.read()
                        _, detected = SecretRedactor.detect_and_redact(content, file_path=rel)
                        findings.extend(detected)
                    except Exception:
                        pass
        return findings

    def _resolve_rules_path(self, repo_path: str) -> Optional[str]:
        if self.rules_path and os.path.exists(self.rules_path):
            return self.rules_path

        # Look for local_rules.yaml in repo_path
        local_candidate = os.path.join(repo_path, "local_rules.yaml")
        if os.path.isfile(local_candidate):
            return local_candidate
        return None

    def _run_semgrep_or_builtin_rules(self, repo_path: str, diff: Optional[str]) -> List[Finding]:
        rules_file = self._resolve_rules_path(repo_path)
        semgrep_path = shutil.which("semgrep")

        if semgrep_path and rules_file:
            try:
                # semgrep scan --metrics=off --sarif --config <rules_file> <target>
                cmd = [
                    semgrep_path,
                    "scan",
                    "--metrics=off",
                    "--sarif",
                    f"--config={rules_file}",
                    repo_path,
                ]
                proc = subprocess.run(cmd, cwd=repo_path, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
                if proc.stdout and proc.stdout.strip().startswith("{"):
                    sarif_findings = SarifNormalizer.normalize(
                        proc.stdout,
                        default_category="security",
                        repo_path=repo_path,
                    )
                    if sarif_findings:
                        return sarif_findings
            except Exception:
                pass

        # Built-in deterministic security rules (executes local_rules.yaml equivalents)
        return self._run_builtin_security_rules(repo_path, diff)

    def _run_builtin_security_rules(self, repo_path: str, diff: Optional[str]) -> List[Finding]:
        findings: List[Finding] = []
        target_files = DiffParser.get_changed_files(diff) if diff is not None else []

        if not target_files:
            for root, _, files in os.walk(repo_path):
                if any(ig in root for ig in [".git", "node_modules", ".venv", "__pycache__"]):
                    continue
                for f in files:
                    if f.endswith(".py") or f.endswith(".js") or f.endswith(".ts"):
                        target_files.append(normalize_path(os.path.relpath(os.path.join(root, f), repo_path)))

        for rel_file in target_files:
            abs_path = os.path.join(repo_path, rel_file) if not os.path.isabs(rel_file) else rel_file
            if not os.path.isfile(abs_path):
                continue
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                lines = content.splitlines()

                # Rule 1: insecure-exec-eval in Python
                if rel_file.endswith(".py"):
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                                if node.func.id in ("eval", "exec"):
                                    line_no = node.lineno
                                    snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                                    sym = resolve_enclosing_symbol(rel_file, line_no, repo_path, snip)
                                    ev = Evidence(
                                        type="ast",
                                        description=f"Arbitrary code execution via {node.func.id}() detected.",
                                        file_path=rel_file,
                                        line_number=line_no,
                                        snippet=snip,
                                    )
                                    findings.append(Finding(
                                        rule_id="semgrep/insecure-exec-eval",
                                        category="security",
                                        severity="critical",
                                        title=f"Insecure {node.func.id}() execution",
                                        message=f"Arbitrary code execution via {node.func.id}() detected.",
                                        file_path=rel_file,
                                        line_number=line_no,
                                        code_snippet=snip,
                                        enclosing_symbol=sym,
                                        evidence=[ev],
                                        confidence=1.0,
                                        fix_suggestion=f"Avoid using {node.func.id}(). Use ast.literal_eval() or safe parser.",
                                    ))

                            # Rule 2: sql-raw-formatting (session.exec(f"...") or session.execute(f"..."))
                            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                                if node.func.attr in ("exec", "execute"):
                                    if node.args and isinstance(node.args[0], ast.JoinedStr):
                                        line_no = node.lineno
                                        snip = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
                                        sym = resolve_enclosing_symbol(rel_file, line_no, repo_path, snip)
                                        ev = Evidence(
                                            type="ast",
                                            description="Potential SQL injection through f-string formatting in database query.",
                                            file_path=rel_file,
                                            line_number=line_no,
                                            snippet=snip,
                                        )
                                        findings.append(Finding(
                                            rule_id="semgrep/sql-raw-formatting",
                                            category="security",
                                            severity="critical",
                                            title="SQL Injection via F-String",
                                            message="Potential SQL injection through f-string formatting in database query.",
                                            file_path=rel_file,
                                            line_number=line_no,
                                            code_snippet=snip,
                                            enclosing_symbol=sym,
                                            evidence=[ev],
                                            confidence=1.0,
                                            fix_suggestion="Use parameterized queries with bind variables.",
                                        ))
                    except Exception:
                        pass

                # Rule 3: js-hardcoded-pat in JS/TS
                if any(rel_file.endswith(ext) for ext in [".js", ".ts", ".jsx", ".tsx"]):
                    pat_pattern = re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})")
                    for idx, line in enumerate(lines, 1):
                        m = pat_pattern.search(line)
                        if m:
                            ev = Evidence(
                                type="regex",
                                description="GitHub Personal Access Token hardcoded in frontend file.",
                                file_path=rel_file,
                                line_number=idx,
                                snippet="[REDACTED_GITHUB_PAT]",
                            )
                            findings.append(Finding(
                                rule_id="semgrep/js-hardcoded-pat",
                                category="security",
                                severity="critical",
                                title="GitHub Personal Access Token exposed",
                                message="GitHub Personal Access Token hardcoded in frontend file.",
                                file_path=rel_file,
                                line_number=idx,
                                code_snippet="[REDACTED_GITHUB_PAT]",
                                enclosing_symbol=resolve_enclosing_symbol(rel_file, idx, repo_path),
                                evidence=[ev],
                                confidence=1.0,
                            ))
            except Exception:
                pass

        return findings
