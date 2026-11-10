# skelion_agent/pr_review/secret_detector.py — Secret Scanning and Redaction
"""
Pre-review secret scanner. Runs before ANY prompt is assembled and before storing evidence.
Detects secrets (API keys, private keys, tokens, credentials), blocks LLM invocation,
redacts secrets into [REDACTED_SECRET], and generates high-severity security findings.
"""

import re
from typing import List, Dict, Any, Tuple


SECRET_PATTERNS = [
    ("AWS Access Key", r"(?i)\b(AKIA[0-9A-Z]{16})\b"),
    ("GitHub Personal Access Token", r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"),
    ("OpenAI/Stripe API Key", r"\b(sk_[live|test]_[0-9a-zA-Z]{24,64})\b"),
    ("Generic Bearer / OpenAI Key", r"\b(sk-[a-zA-Z0-9]{32,64})\b"),
    ("Private Key Header", r"-----BEGIN\s+(?:RSA|EC|DSA|OPENSSH|PGP|ENCRYPTED|PRIVATE)?\s*KEY-----"),
    ("Slack Token", r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"),
    ("Generic Password in URI", r"://[a-zA-Z0-9_.+-]+:([a-zA-Z0-9_.~!$&'()*+,;=-]+)@[a-zA-Z0-9.-]+"),
]


class SecretMatch:
    def __init__(self, secret_type: str, match_text: str, start_index: int, end_index: int, line_number: int):
        self.secret_type = secret_type
        self.match_text = match_text
        self.start_index = start_index
        self.end_index = end_index
        self.line_number = line_number

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.secret_type,
            "line_number": self.line_number,
            "redacted": f"[REDACTED_{self.secret_type.upper().replace(' ', '_')}]"
        }


def scan_for_secrets(text: str) -> List[SecretMatch]:
    """Scan text for known secret patterns."""
    if not text:
        return []
    matches: List[SecretMatch] = []
    lines = text.splitlines(keepends=True)

    char_offset = 0
    for line_idx, line in enumerate(lines, start=1):
        for sec_name, pattern in SECRET_PATTERNS:
            for m in re.finditer(pattern, line):
                matched_str = m.group(1) if m.groups() else m.group(0)
                matches.append(
                    SecretMatch(
                        secret_type=sec_name,
                        match_text=matched_str,
                        start_index=char_offset + m.start(),
                        end_index=char_offset + m.end(),
                        line_number=line_idx,
                    )
                )
        char_offset += len(line)
    return matches


def redact_secrets(text: str) -> str:
    """Redact all discovered secret patterns from text."""
    if not text:
        return ""
    result = text
    for sec_name, pattern in SECRET_PATTERNS:
        replacement = f"[REDACTED_{sec_name.upper().replace(' ', '_')}]"
        # If there is a capture group, replace the capture group
        def _repl(match):
            full = match.group(0)
            if match.groups():
                captured = match.group(1)
                return full.replace(captured, replacement)
            return replacement

        result = re.sub(pattern, _repl, result)
    return result
