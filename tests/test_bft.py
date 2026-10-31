import pytest
from gossipmesh.consensus.bft import BFTVote, BFTQuorumEngine


def test_bft_empty_votes():
    engine = BFTQuorumEngine()
    result = engine.evaluate_quorum([])
    assert result.is_consensus_reached is False
    assert result.total_votes == 0
    assert result.approval_ratio == 0.0


def test_bft_quorum_reached():
    engine = BFTQuorumEngine(quorum_threshold=0.66, min_score=75)
    votes = [
        BFTVote(node_id="node-1", verdict="APPROVE", score=90),
        BFTVote(node_id="node-2", verdict="APPROVE", score=85),
        BFTVote(node_id="node-3", verdict="REJECT", score=50),
    ]
    result = engine.evaluate_quorum(votes)
    assert result.is_consensus_reached is True
    assert result.approval_ratio == pytest.approx(2.0 / 3.0, rel=1e-2)
    assert result.approvals == 2
    assert result.rejections == 1


def test_bft_quorum_failed_below_threshold():
    engine = BFTQuorumEngine(quorum_threshold=0.66, min_score=80)
    votes = [
        BFTVote(node_id="node-1", verdict="APPROVE", score=85),
        BFTVote(node_id="node-2", verdict="REJECT", score=40),
        BFTVote(node_id="node-3", verdict="REJECT", score=30),
    ]
    result = engine.evaluate_quorum(votes)
    assert result.is_consensus_reached is False
    assert result.approval_ratio == pytest.approx(1.0 / 3.0, rel=1e-2)


def test_bft_weighted_voting():
    engine = BFTQuorumEngine(
        quorum_threshold=0.7,
        min_score=80,
        weights={"trusted-node": 3.0, "ordinary-node": 1.0},
    )
    votes = [
        BFTVote(node_id="trusted-node", verdict="APPROVE", score=95),
        BFTVote(node_id="ordinary-node", verdict="REJECT", score=50),
    ]
    result = engine.evaluate_quorum(votes)
    # trusted-node weight 3.0 out of total 4.0 = 0.75 ratio
    assert result.is_consensus_reached is True
    assert result.approval_ratio == 0.75
