# skelion_agent/pr_review_lanes/filter_and_rank.py — Citation Filter & Noise Control / Ranker
"""
Citation Filter & Noise Control / Ranker:
1. Drop any findings whose line numbers do not fall inside added or modified lines in the diff.
2. Drop any finding lacking at least one verifiable evidence item.
3. Score & rank findings: score = severity_weight * confidence * (1 + impact_factor) * evidence_strength.
4. Cap inline findings to maximum 10 (configurable), overflowing extra findings into the summary.
"""

from typing import List, Dict, Set, Optional, Tuple
from pydantic import BaseModel, Field
from .models import Finding, DEFAULT_SEVERITY_WEIGHTS
from .diff_parser import DiffParser, normalize_path


class FilterRankResult(BaseModel):
    """Result of citation filtering and ranking."""
    inline_findings: List[Finding] = Field(default_factory=list)
    summary_findings: List[Finding] = Field(default_factory=list)
    all_ranked_findings: List[Finding] = Field(default_factory=list)
    dropped_out_of_diff: List[Finding] = Field(default_factory=list)
    dropped_no_evidence: List[Finding] = Field(default_factory=list)
    dropped_out_of_diff_count: int = 0
    dropped_no_evidence_count: int = 0
    total_input_count: int = 0
    total_surviving_count: int = 0


class CitationFilterAndRanker:
    """Implements noise control, diff citation verification, scoring, and inline capping."""

    def __init__(
        self,
        max_inline: int = 10,
        severity_weights: Optional[Dict[str, float]] = None,
    ):
        self.max_inline = max_inline
        self.severity_weights = severity_weights or DEFAULT_SEVERITY_WEIGHTS

    def is_line_in_diff(
        self,
        finding_file: str,
        line_number: Optional[int],
        diff_map: Dict[str, Set[int]],
    ) -> bool:
        """Checks if a finding's line number falls within the added/modified lines in diff."""
        if line_number is None or line_number <= 0:
            return False

        norm_finding_file = normalize_path(finding_file)

        # Exact match
        if norm_finding_file in diff_map:
            return line_number in diff_map[norm_finding_file]

        # Suffix / relative match (e.g., repo/sub/file.py vs sub/file.py)
        for diff_file, lines in diff_map.items():
            if norm_finding_file.endswith(diff_file) or diff_file.endswith(norm_finding_file):
                return line_number in lines

        return False

    def has_verifiable_evidence(self, finding: Finding) -> bool:
        """Verifies if the finding has at least one valid evidence item."""
        if not finding.evidence or len(finding.evidence) == 0:
            return False

        for ev in finding.evidence:
            if ev.is_verifiable():
                return True
        return False

    def calculate_score(self, finding: Finding) -> float:
        """
        Calculates ranking score using the canonical formula:
        score = severity_weight * confidence * (1 + impact_factor) * evidence_strength
        """
        sev_key = (finding.severity or "medium").lower()
        sev_weight = finding.severity_weight if finding.severity_weight > 0 else self.severity_weights.get(sev_key, 3.0)
        confidence = max(0.0, min(1.0, finding.confidence))
        impact_factor = max(0.0, finding.impact_factor)
        evidence_strength = max(0.0, finding.evidence_strength)

        return float(sev_weight * confidence * (1.0 + impact_factor) * evidence_strength)

    def filter_and_rank(
        self,
        findings: List[Finding],
        diff_text: Optional[str] = None,
        max_inline: Optional[int] = None,
    ) -> FilterRankResult:
        """
        Applies citation filtering against diff and evidence verification,
        scores surviving findings, sorts descending, and splits into inline vs summary.
        """
        cap = self.max_inline if max_inline is None else max_inline
        diff_map = DiffParser.parse(diff_text) if diff_text else {}
        require_diff_check = bool(diff_text is not None)

        surviving: List[Finding] = []
        dropped_diff: List[Finding] = []
        dropped_evidence: List[Finding] = []

        for f in findings:
            # 1. Evidence Verification: Drop if lacking verifiable evidence
            if not self.has_verifiable_evidence(f):
                dropped_evidence.append(f)
                continue

            # 2. Diff Citation Verification: Drop if line number not inside added/modified lines in diff
            if require_diff_check:
                if not self.is_line_in_diff(f.file_path, f.line_number, diff_map):
                    dropped_diff.append(f)
                    continue

            # Calculate and store canonical score
            f.score = self.calculate_score(f)
            surviving.append(f)

        # 3. Score & Rank: Sort descending by score, tie-breaker: line_number, rule_id
        surviving.sort(
            key=lambda x: (
                x.score,
                -(x.line_number or 0),
                x.rule_id,
            ),
            reverse=True,
        )

        # 4. Cap inline findings to maximum 10 (or configured cap), overflowing extra into summary
        inline_list: List[Finding] = []
        summary_list: List[Finding] = []

        for idx, item in enumerate(surviving):
            if idx < cap:
                item.is_inline = True
                item.overflowed_to_summary = False
                inline_list.append(item)
            else:
                item.is_inline = False
                item.overflowed_to_summary = True
                summary_list.append(item)

        return FilterRankResult(
            inline_findings=inline_list,
            summary_findings=summary_list,
            all_ranked_findings=surviving,
            dropped_out_of_diff=dropped_diff,
            dropped_no_evidence=dropped_evidence,
            dropped_out_of_diff_count=len(dropped_diff),
            dropped_no_evidence_count=len(dropped_evidence),
            total_input_count=len(findings),
            total_surviving_count=len(surviving),
        )


def filter_and_rank_findings(
    findings: List[Finding],
    diff_text: Optional[str] = None,
    max_inline: int = 10,
) -> FilterRankResult:
    """Convenience helper function for citation filtering and ranking."""
    ranker = CitationFilterAndRanker(max_inline=max_inline)
    return ranker.filter_and_rank(findings, diff_text=diff_text)
