# tests/test_mcp_server.py — Skelion MCP Server Tool Tests

import pytest
from skelion_mcp.server import SkelionMCPServer, MCP_TOOLS
from skelion_agent.models import Incident
from sqlmodel import Session


def test_mcp_tool_definitions():
    server = SkelionMCPServer()
    tool_names = [t["name"] for t in MCP_TOOLS]
    assert "list_incidents" in tool_names
    assert "get_incident" in tool_names
    assert "get_service_health" in tool_names
    assert "get_fix_status" in tool_names
    assert "run_replay_test" in tool_names
    assert "propose_fix" in tool_names


def test_mcp_service_health():
    server = SkelionMCPServer()
    health = server.handle_tool_call("get_service_health", {"window": "1h"})
    assert "status" in health
    assert "availability_pct" in health
    assert "latency_p95_ms" in health


def test_mcp_propose_fix_and_replay():
    server = SkelionMCPServer()
    # Insert or query mock incident
    with Session(server.engine) as s:
        inc = Incident(
            id="inc_test_mcp_123",
            org_id="org_default",
            route_path="/api/test_checkout",
            http_method="GET",
            captured_method="GET",
            status_code=500,
            error_summary="Null pointer in checkout controller",
            fingerprint="fp_test_12345",
        )
        s.merge(inc)
        s.commit()

    res = server.handle_tool_call("propose_fix", {"incident_id": "inc_test_mcp_123"})
    assert res["incident_id"] == "inc_test_mcp_123"
    assert "proposed_diff" in res
    assert "verification" in res
    assert res["verification"]["passed"] >= 1
    assert res["confidence_score"] > 0.0
