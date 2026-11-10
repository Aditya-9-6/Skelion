# skelion_agent/pr_review_lanes/models.py — Standard Models for PR Review Lanes
"""
Standard data models for PR review lanes, findings, evidence, and results.
Provides stable fingerprinting, severity weights, and evidence verification.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import hashlib
import uuid


def compute_fingerprint(
    rule_id_or_category: str,
    normalized_code_snippet: Optional[str],
    enclosing_symbol: Optional[str],
    file_path: Optional[str],
) -> str:
    """
    Computes a stable fingerprint for a finding:
    fingerprint = hash(rule_id_or_category, normalized_code_snippet, enclosing_symbol, file_path_at_symbol_level)
    """
    norm_rule = (rule_id_or_category or "").strip()
    norm_snippet = " ".join((normalized_code_snippet or "").split())
    norm_symbol = (enclosing_symbol or "").strip()
    norm_file = (file_path or "").replace("\\", "/").strip()

    payload = f"{norm_rule}:{norm_snippet}:{norm_symbol}:{norm_file}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Evidence(BaseModel):
    """Verifiable evidence item supporting a finding."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "ast"  # ast, regex, sarif, diff, runtime, license, typosquat
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    end_line: Optional[int] = None
    snippet: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_verifiable(self) -> bool:
        """Checks if the evidence contains verifiable non-empty information."""
        if not self.description or not self.description.strip():
            return False
        # Must have snippet or file_path+line_number or non-empty metadata
        if (self.snippet and self.snippet.strip()) or (self.file_path and self.line_number is not None):
            return True
        if self.metadata and len(self.metadata) > 0:
            return True
        return bool(self.description.strip())


DEFAULT_SEVERITY_WEIGHTS: Dict[str, float] = {
    "critical": 5.0,
    "high": 4.0,
    "error": 4.0,
    "medium": 3.0,
    "warning": 3.0,
    "low": 2.0,
    "info": 1.0,
    "note": 1.0,
}


class Finding(BaseModel):
    """Standard normalized review finding produced by any lane or SARIF tool."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str
    category: str  # quality, security, dependency, performance, ai_sanity, runtime
    severity: str = "medium"  # critical, high, medium, low, info (or error, warning, note)
    title: str = ""
    message: str = ""
    file_path: str = ""
    line_number: Optional[int] = None
    end_line: Optional[int] = None
    column_number: Optional[int] = None
    end_column: Optional[int] = None
    code_snippet: Optional[str] = None
    normalized_code_snippet: Optional[str] = None
    enclosing_symbol: Optional[str] = None
    fingerprint: str = ""
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: float = 1.0  # 0.0 to 1.0
    severity_weight: float = 0.0  # If 0.0, derived from severity
    impact_factor: float = 0.0  # >= 0.0, e.g. from runtime traffic/errors
    evidence_strength: float = 1.0  # 0.0 to 1.0+
    score: float = 0.0
    is_inline: bool = True
    overflowed_to_summary: bool = False
    fix_suggestion: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        # Populate normalized snippet if not set
        if not self.normalized_code_snippet and self.code_snippet:
            self.normalized_code_snippet = " ".join(self.code_snippet.split())

        # Populate stable fingerprint if not set
        if not self.fingerprint:
            rule_or_cat = self.rule_id or self.category
            self.fingerprint = compute_fingerprint(
                rule_or_cat,
                self.normalized_code_snippet or self.code_snippet,
                self.enclosing_symbol,
                self.file_path,
            )

        # Derive severity_weight if not explicitly provided
        if self.severity_weight <= 0.0:
            sev_key = (self.severity or "medium").lower()
            self.severity_weight = DEFAULT_SEVERITY_WEIGHTS.get(sev_key, 3.0)

        # Calculate score if not explicitly set
        if self.score <= 0.0:
            self.score = self.calculate_score()

    def calculate_score(self) -> float:
        """
        Calculates score:
        score = severity_weight * confidence * (1 + impact_factor) * evidence_strength
        """
        sev_w = self.severity_weight if self.severity_weight > 0 else DEFAULT_SEVERITY_WEIGHTS.get((self.severity or "medium").lower(), 3.0)
        return float(sev_w * self.confidence * (1.0 + self.impact_factor) * self.evidence_strength)


class LaneResult(BaseModel):
    """Result returned by any PR review lane execution."""
    lane_id: str
    name: str
    status: str  # "ran", "skipped: <reason>", "failed: <reason>"
    duration_seconds: float = 0.0
    tool_version: Optional[str] = None
    findings: List[Finding] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
