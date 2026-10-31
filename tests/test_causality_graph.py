from skelion_agent.causality import CausalityGraph


def test_causality_graph_root_cause_identification():
    cg = CausalityGraph()
    spans = [
        {
            "span_id": "span-1",
            "parent_span_id": None,
            "service": "gateway",
            "name": "GET /api",
            "duration_ms": 1200.0,
            "status_code": 500,
            "error": True,
        },
        {
            "span_id": "span-2",
            "parent_span_id": "span-1",
            "service": "auth-service",
            "name": "VerifyToken",
            "duration_ms": 1100.0,
            "status_code": 500,
            "error": True,
        },
        {
            "span_id": "span-3",
            "parent_span_id": "span-2",
            "service": "redis",
            "name": "GET session",
            "duration_ms": 1050.0,
            "status_code": 503,
            "error": True,
        },
    ]
    cg.build_from_spans(spans)

    root_cause = cg.find_root_cause()
    assert root_cause == "span-1"

    path = cg.get_upstream_path("span-3")
    assert path == ["span-1", "span-2", "span-3"]


def test_causality_graph_timeout_cascade():
    cg = CausalityGraph()
    spans = [
        {
            "span_id": "a",
            "parent_span_id": None,
            "service": "api",
            "name": "handler",
            "duration_ms": 50.0,
            "status_code": 200,
        },
        {
            "span_id": "b",
            "parent_span_id": "a",
            "service": "db",
            "name": "query",
            "duration_ms": 5000.0,
            "status_code": 200,
        },
    ]
    cg.build_from_spans(spans)

    root_cause = cg.find_root_cause()
    assert root_cause == "b"
