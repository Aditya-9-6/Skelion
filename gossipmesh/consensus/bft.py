"""
Byzantine Fault Tolerant (BFT) Voting Quorum Engine for GossipMesh.
Enforces 2/3 majority consensus across multi-model architectural proposals and agent actions.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("gossipmesh.consensus.bft")


class BFTVote:
    """Represents an individual node or model signature-backed vote in the BFT consensus pool."""

    def __init__(
        self,
        node_id: str,
        verdict: str,
        score: int,
        signature: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.verdict = verdict.upper()  # APPROVE, REJECT, ABSTAIN
        self.score = max(0, min(100, score))
        self.signature = signature
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "verdict": self.verdict,
            "score": self.score,
            "signature": self.signature,
            "metadata": self.metadata,
        }


class BFTConsensusResult:
    """Holds the outcome of a BFT quorum evaluation epoch."""

    def __init__(
        self,
        is_consensus_reached: bool,
        approval_ratio: float,
        total_votes: int,
        approvals: int,
        rejections: int,
        abstentions: int,
        quorum_threshold: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.is_consensus_reached = is_consensus_reached
        self.approval_ratio = approval_ratio
        self.total_votes = total_votes
        self.approvals = approvals
        self.rejections = rejections
        self.abstentions = abstentions
        self.quorum_threshold = quorum_threshold
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_consensus_reached": self.is_consensus_reached,
            "approval_ratio": round(self.approval_ratio, 4),
            "total_votes": self.total_votes,
            "approvals": self.approvals,
            "rejections": self.rejections,
            "abstentions": self.abstentions,
            "quorum_threshold": self.quorum_threshold,
            "details": self.details,
        }


class BFTQuorumEngine:
    """Engine enforcing Byzantine Fault Tolerant 2/3 majority quorum voting."""

    def __init__(
        self,
        quorum_threshold: float = 0.6667,
        min_score: int = 80,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.quorum_threshold = quorum_threshold
        self.min_score = min_score
        self.weights = weights or {}

    def evaluate_quorum(self, votes: List[BFTVote]) -> BFTConsensusResult:
        if not votes:
            return BFTConsensusResult(
                is_consensus_reached=False,
                approval_ratio=0.0,
                total_votes=0,
                approvals=0,
                rejections=0,
                abstentions=0,
                quorum_threshold=self.quorum_threshold,
                details={"reason": "No votes submitted"},
            )

        total_weight = 0.0
        approval_weight = 0.0
        approvals_count = 0
        rejections_count = 0
        abstentions_count = 0

        for vote in votes:
            w = self.weights.get(vote.node_id, 1.0)
            total_weight += w

            if vote.verdict == "APPROVE" and vote.score >= self.min_score:
                approval_weight += w
                approvals_count += 1
            elif vote.verdict == "REJECT" or vote.score < self.min_score:
                rejections_count += 1
            else:
                abstentions_count += 1

        approval_ratio = (approval_weight / total_weight) if total_weight > 0 else 0.0
        is_reached = approval_ratio >= self.quorum_threshold

        return BFTConsensusResult(
            is_consensus_reached=is_reached,
            approval_ratio=approval_ratio,
            total_votes=len(votes),
            approvals=approvals_count,
            rejections=rejections_count,
            abstentions=abstentions_count,
            quorum_threshold=self.quorum_threshold,
            details={
                "total_weight": total_weight,
                "approval_weight": approval_weight,
            },
        )
