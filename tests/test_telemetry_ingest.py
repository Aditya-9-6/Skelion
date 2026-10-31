from skelion_agent.telemetry import TailSampledSpanBuffer


def test_telemetry_ingestion_happy_path():
    buffer = TailSampledSpanBuffer(
        max_size=100, error_sample_ratio=1.0, default_sample_ratio=1.0
    )
    headers = {"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
    span = {
        "name": "test-span",
        "status_code": 200,
        "attributes": {"agent.id": "agent_123"},
    }

    retained = buffer.ingest_span(span, headers=headers)
    assert retained is True

    spans = buffer.get_spans()
    assert len(spans) == 1
    assert spans[0]["w3c_traceparent"] == headers["traceparent"]
    assert spans[0]["attributes"]["agent.id"] == "agent_123"


def test_tail_sampling_error_spans():
    # Force error sampling to 1.0 and default sampling to 0.0
    buffer = TailSampledSpanBuffer(
        max_size=100, error_sample_ratio=1.0, default_sample_ratio=0.0
    )

    normal_span = {"name": "normal-op", "status_code": 200}
    error_span = {"name": "failed-op", "status_code": 500}

    assert buffer.ingest_span(normal_span) is False
    assert buffer.ingest_span(error_span) is True

    spans = buffer.get_spans()
    assert len(spans) == 1
    assert spans[0]["name"] == "failed-op"
    assert buffer.stats["error_count"] == 1
    assert buffer.stats["total_ingested"] == 2


def test_buffer_capacity_bounded():
    buffer = TailSampledSpanBuffer(
        max_size=5, error_sample_ratio=1.0, default_sample_ratio=1.0
    )
    for i in range(10):
        buffer.ingest_span({"name": f"span-{i}", "status_code": 200})

    spans = buffer.get_spans()
    assert len(spans) == 5
    assert spans[0]["name"] == "span-5"
    assert spans[-1]["name"] == "span-9"
