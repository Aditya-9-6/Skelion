# skelion_agent/pr_review/fingerprint.py — Deterministic Finding Fingerprints
"""
Fingerprint generation:
fingerprint = hash(rule_id_or_category, normalized_code_snippet, enclosing_symbol, file_path_at_symbol_level)
Line numbers are omitted so findings survive edits and commits above them.
"""

import hashlib
import re


def normalize_code_snippet(code: str) -> str:
    """Normalize code snippet by stripping trailing whitespace and collapsing extra empty lines."""
    if not code:
        return ""
    lines = [line.rstrip() for line in code.splitlines()]
    # remove leading and trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def generate_fingerprint(
    rule_id_or_category: str,
    code_snippet: str,
    enclosing_symbol: str,
    file_path: str,
) -> str:
    """
    Computes a deterministic SHA-256 fingerprint for a finding.
    Omit line numbers so findings remain stable when unrelated code is edited.
    """
    normalized_code = normalize_code_snippet(code_snippet)
    # Normalize path separators to forward slashes
    norm_path = file_path.replace("\\", "/")
    # Normalize symbol
    norm_symbol = enclosing_symbol.strip() if enclosing_symbol else "<module>"
    # Normalize rule
    norm_rule = rule_id_or_category.strip()

    raw = f"{norm_rule}::{norm_path}::{norm_symbol}::{normalized_code}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
