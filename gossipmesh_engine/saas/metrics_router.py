# gossipmesh/saas/metrics_router.py
"""Metrics router for the GossipMesh SaaS sidecar.
Provides endpoint(s) to expose cycle counts and PR‑throughput estimates.
"""

from fastapi import APIRouter
import gossipmesh.metrics as metrics

router = APIRouter()

@router.get("/", summary="Current cycle metrics")
async def get_metrics():
    """Return the number of cycles in the last 24 h and the estimated PRs per day."""
    return {
        "cycles_last_24h": metrics.count_cycles_last(24),
        "estimated_prs_per_day": metrics.estimate_prs_per_day(),
    }
