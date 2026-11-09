# skelion_agent/pr_review_lanes/__init__.py — Unified PR Review Lanes & Security Architecture
"""
Skelion PR Review Lanes:
- L1 Quality: Deterministic quality adapter (Ruff, ESLint, tsc, mypy).
- L2 Security: Security adapter (Semgrep --metrics=off, local_rules.yaml, Gitleaks, pre-prompt secret redaction).
- L3 Dependencies: OSV-Scanner adapter on changed lockfiles, licensing, typosquat heuristics.
- L7 Performance: Static performance rules (N+1 queries, blocking calls in async handlers, unbounded loops/queries).
- L9 Runtime: Runtime-aware impact lane (maps changed symbols to routes, traffic share, error spikes; skips if disconnected).
- L10 AI Sanity: AI-code sanity checker (hallucinated imports, non-existent methods on types, duplicate blocks).
- SARIF Normalizer: Standard SARIF 2.1.0 output normalizer with stable fingerprinting.
- Citation Filter & Ranker: Noise control, diff citations, evidence verification, inline capping.
"""

from .models import (
    Evidence,
    Finding,
    LaneResult,
    compute_fingerprint,
    DEFAULT_SEVERITY_WEIGHTS,
)
from .base_lane import BaseLane
from .diff_parser import DiffParser, normalize_path
from .sarif_normalizer import SarifNormalizer, resolve_enclosing_symbol
from .filter_and_rank import (
    CitationFilterAndRanker,
    FilterRankResult,
    filter_and_rank_findings,
)
from .l1_quality import L1QualityLane
from .l2_security import (
    L2SecurityLane,
    SecretRedactor,
    redact_prompt,
    detect_and_redact_secrets,
)
from .l3_dependencies import (
    L3DependenciesLane,
    check_typosquatting,
    levenshtein_distance,
)
from .l7_performance import L7PerformanceLane
from .l9_runtime import L9RuntimeLane
from .l10_ai_sanity import L10AiSanityLane

__all__ = [
    # Models
    "Evidence",
    "Finding",
    "LaneResult",
    "compute_fingerprint",
    "DEFAULT_SEVERITY_WEIGHTS",
    # Base
    "BaseLane",
    # Diff & SARIF
    "DiffParser",
    "normalize_path",
    "SarifNormalizer",
    "resolve_enclosing_symbol",
    # Citation Filter & Ranker
    "CitationFilterAndRanker",
    "FilterRankResult",
    "filter_and_rank_findings",
    # Lanes
    "L1QualityLane",
    "L2SecurityLane",
    "L3DependenciesLane",
    "L7PerformanceLane",
    "L9RuntimeLane",
    "L10AiSanityLane",
    # Utilities
    "SecretRedactor",
    "redact_prompt",
    "detect_and_redact_secrets",
    "check_typosquatting",
    "levenshtein_distance",
]
