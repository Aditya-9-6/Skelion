# skelion_agent/waf_routes.py — Spryzen WAF Telemetry & Diagnostics API
"""
API endpoints for inspecting Spryzen WAF status, blocked threats, Tartarus deception events,
and testing security payloads.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from skelion_edge.waf_shield import (
    get_waf_metrics,
    get_recent_threats,
    scan_payload_for_threats,
    inspect_request_security,
)

router = APIRouter(prefix="/v1/waf", tags=["Spryzen WAF Shield"])


class TestPayloadRequest(BaseModel):
    payload: str
    method: Optional[str] = "GET"
    path: Optional[str] = "/"


@router.get("/metrics")
async def get_metrics():
    """Retrieve aggregate WAF counters and security protection metrics."""
    return get_waf_metrics()


@router.get("/events")
async def get_events(limit: int = Query(default=50, ge=1, le=200)):
    """Retrieve the most recent security attacks blocked by the WAF or trapped by Tartarus."""
    return {
        "status": "ok",
        "events": get_recent_threats(limit=limit)
    }


@router.post("/test-payload")
async def test_payload(body: TestPayloadRequest):
    """Diagnose and simulate how Spryzen WAF evaluates a specific request or string."""
    is_blocked, threat, deception = inspect_request_security(
        method=body.method or "GET",
        path=body.path or "/",
        body=body.payload
    )
    return {
        "is_blocked": is_blocked,
        "threat": threat,
        "deception_triggered": deception is not None,
        "engine": "Spryzen Ingress WAF Shield"
    }
