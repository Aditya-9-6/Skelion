# skelion_agent/pr_review/lanes/base.py — Lane Adapter Base Interface
"""
Base interface and data contracts for all PR Review Lanes (L1 through L11).
Every lane reports:
- status: "ran", "skipped: <reason>", or "failed: <reason>"
- tool version
- duration in milliseconds
- normalized findings list with attached evidence
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from skelion_agent.pr_review.context import PRContext
from skelion_agent.pr_review.config import SkelionRepoConfig


class FindingDraft(BaseModel):
    rule_id: str
    category: str = "quality"  # quality, security, dependencies, breaking, migrations, performance, logic, ai_sanity
    file_path: str
    start_line: int
    end_line: int
    severity: str = "medium"  # info, low, medium, high, critical
    confidence: float = 1.0
    impact_factor: float = 0.0
    claim: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)  # [{type, ref, payload}]
    suggested_fix: Optional[str] = None
    enclosing_symbol: str = "<module>"
    code_snippet: str = ""


class LaneOutput(BaseModel):
    lane_id: str
    name: str
    status: str  # "ran", "skipped: <reason>", "failed: <reason>"
    version: str = "1.0.0"
    duration_ms: float = 0.0
    findings: List[FindingDraft] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseLane(ABC):
    lane_id: str = "L0"
    name: str = "Base Lane"

    @abstractmethod
    def run(self, context: PRContext, config: SkelionRepoConfig) -> LaneOutput:
        """Run lane analysis on PR context and return LaneOutput."""
        pass
