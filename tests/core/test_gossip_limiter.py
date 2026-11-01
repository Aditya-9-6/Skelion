import time
import pytest
from skelion_agent.core.gossip_limiter import GossipRateLimiter, RateLimitExceededError


def test_gossip_limiter_basic_consumption():
    limiter = GossipRateLimiter(node_id="node-1", capacity=5.0, refill_rate=1.0)
    
    # Consume 3 tokens successfully
    allowed, remaining, reset_time = limiter.check_and_consume("user-123", 3.0)
    assert allowed is True
    assert remaining == 2.0
    assert reset_time > time.time()

    # Consume remaining 2 tokens
    allowed, remaining, reset_time = limiter.check_and_consume("user-123", 2.0)
    assert allowed is True
    assert remaining == 0.0

    # Next consumption should fail
    allowed, remaining, reset_time = limiter.check_and_consume("user-123", 1.0)
    assert allowed is False


def test_gossip_limiter_enforce_exception():
    limiter = GossipRateLimiter(node_id="node-1", capacity=1.0, refill_rate=0.1)
    limiter.enforce("user-456", 1.0)

    with pytest.raises(RateLimitExceededError) as exc_info:
        limiter.enforce("user-456", 1.0)
    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.message


def test_gossip_synchronization_and_reconciliation():
    limiter_a = GossipRateLimiter(node_id="node-A", capacity=10.0, refill_rate=2.0)
    limiter_b = GossipRateLimiter(node_id="node-B", capacity=10.0, refill_rate=2.0)

    # Node A consumes 8 tokens
    limiter_a.check_and_consume("shared-user", 8.0)
    
    # Extract gossip state from Node A and propagate to Node B
    state_a = limiter_a.get_gossip_state("shared-user")
    limiter_b.receive_gossip(state_a)

    # Node B should now reflect Node A's reduced capacity (approx 2 tokens remaining)
    allowed, remaining, _ = limiter_b.check_and_consume("shared-user", 3.0)
    assert allowed is False
    assert remaining <= 2.0

    # Vector clock should incorporate node-A updates
    assert limiter_b.vector_clock.get_time("node-A") > 0
