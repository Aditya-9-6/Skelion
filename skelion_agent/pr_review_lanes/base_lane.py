# skelion_agent/pr_review_lanes/base_lane.py — Base Abstract Class for PR Review Lanes
"""
Base abstract class for PR review lanes.
Manages execution status ('ran', 'skipped: <reason>', 'failed: <reason>'),
execution duration tracking, and tool version reporting.
"""

from abc import ABC, abstractmethod
import time
from typing import Optional, Dict, Any, List
from .models import LaneResult, Finding


class BaseLane(ABC):
    """
    Abstract base class for all PR review lanes.
    Standardizes lifecycle management, status reporting, timing, and error handling.
    """

    def __init__(self, lane_id: str, name: str, category: str):
        self.lane_id = lane_id
        self.name = name
        self.category = category

    @abstractmethod
    def get_tool_version(self) -> Optional[str]:
        """Returns the version of the underlying tool, or None if unavailable/not applicable."""
        pass

    def check_prerequisites(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Validates prerequisites for running this lane.
        Returns a string reason if the lane should be skipped, or None to proceed.
        """
        return None

    @abstractmethod
    def execute(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        """
        Executes the lane's specific analysis logic and returns a list of Findings.
        May raise exceptions, which are caught and converted to 'failed: <reason>' status by run().
        """
        pass

    def run(
        self,
        repo_path: str,
        diff: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> LaneResult:
        """
        Runs the lane lifecycle:
        1. Checks prerequisites -> 'skipped: <reason>' if not satisfied
        2. Measures execution duration
        3. Invokes execute() -> 'ran' if success, or 'failed: <reason>' on uncaught exception
        4. Reports tool version and findings
        """
        start_time = time.perf_counter()
        tool_version = self.get_tool_version()

        # Check prerequisite / skip condition
        skip_reason = self.check_prerequisites(repo_path, diff, context)
        if skip_reason:
            duration = round(time.perf_counter() - start_time, 4)
            return LaneResult(
                lane_id=self.lane_id,
                name=self.name,
                status=f"skipped: {skip_reason}",
                duration_seconds=duration,
                tool_version=tool_version,
                findings=[],
                metadata={"skip_reason": skip_reason},
            )

        try:
            findings = self.execute(repo_path, diff, context)
            duration = round(time.perf_counter() - start_time, 4)
            return LaneResult(
                lane_id=self.lane_id,
                name=self.name,
                status="ran",
                duration_seconds=duration,
                tool_version=tool_version,
                findings=findings,
                metadata={"findings_count": len(findings)},
            )
        except Exception as e:
            duration = round(time.perf_counter() - start_time, 4)
            return LaneResult(
                lane_id=self.lane_id,
                name=self.name,
                status=f"failed: {str(e)}",
                duration_seconds=duration,
                tool_version=tool_version,
                findings=[],
                error=str(e),
                metadata={"error_type": type(e).__name__},
            )
